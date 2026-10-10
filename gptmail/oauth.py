"""Single-owner OAuth 2.1 authorization-code + PKCE server for ChatGPT MCP.

Uses Dynamic Client Registration (DCR), supported by ChatGPT. Client metadata
(CIMD) is intentionally not advertised until its validation is implemented.
"""
from __future__ import annotations

import base64
import hashlib
import html
import re
import secrets
from urllib.parse import urlencode, parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .auth import (verify_password, validate_redirect, redirect_origin, client_ip, rate_limit,
                   token_hash, issue_tokens, auth_epoch)
from .config import base_url, resource_url
from .store import get_json, set_json, pop_json

router = APIRouter()


def metadata():
    base = base_url()
    return {
        'issuer': base,
        'authorization_endpoint': base + '/oauth/authorize',
        'token_endpoint': base + '/oauth/token',
        'registration_endpoint': base + '/oauth/register',
        'response_types_supported': ['code'],
        'grant_types_supported': ['authorization_code', 'refresh_token'],
        'token_endpoint_auth_methods_supported': ['none'],
        'code_challenge_methods_supported': ['S256'],
        'scopes_supported': ['mail'],
        'authorization_response_iss_parameter_supported': True,
    }


@router.get('/.well-known/oauth-authorization-server')
def auth_discovery():
    return metadata()


@router.get('/.well-known/oauth-protected-resource')
@router.get('/.well-known/oauth-protected-resource/mcp')
def resource_discovery():
    return {'resource': resource_url(), 'authorization_servers': [base_url()],
            'bearer_methods_supported': ['header'], 'scopes_supported': ['mail']}


def _client(client_id):
    if not isinstance(client_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{12,100}', client_id):
        raise HTTPException(400, 'Invalid client_id.')
    stored = get_json('gptmail:oauth:client:' + client_id)
    if not stored:
        raise HTTPException(400, 'Unknown OAuth client.')
    return stored


@router.post('/oauth/register')
async def register(request: Request):
    rate_limit('register', client_ip(request), max_count=20, window=3600)
    try:
        obj = await request.json()
    except Exception:
        raise HTTPException(400, 'Invalid registration JSON.')
    redirects = obj.get('redirect_uris', []) if isinstance(obj, dict) else []
    if (not isinstance(redirects, list) or not 1 <= len(redirects) <= 8
            or not all(validate_redirect(uri) for uri in redirects)
            or obj.get('token_endpoint_auth_method', 'none') != 'none'):
        raise HTTPException(400, 'Public OAuth client with valid redirect_uris required.')
    client_id = secrets.token_urlsafe(24)
    name = str(obj.get('client_name', 'MCP client'))[:120]
    stored = {'client_id': client_id, 'redirect_uris': redirects, 'client_name': name}
    set_json('gptmail:oauth:client:' + client_id, stored)
    return JSONResponse({**stored, 'token_endpoint_auth_method': 'none',
                         'grant_types': ['authorization_code', 'refresh_token'],
                         'response_types': ['code']}, status_code=201,
                        headers={'Cache-Control': 'no-store'})


def _validate_auth_query(data):
    client_id = data.get('client_id', '')
    client = _client(client_id)
    redirect_uri = data.get('redirect_uri', '')
    challenge = data.get('code_challenge', '')
    method = data.get('code_challenge_method', '')
    resource = data.get('resource', resource_url())
    if (redirect_uri not in client['redirect_uris'] or not validate_redirect(redirect_uri)
            or data.get('response_type') != 'code'
            or not isinstance(challenge, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', challenge)
            or method != 'S256' or resource not in (base_url(), resource_url())
            or data.get('scope', 'mail') not in ('', 'mail')):
        raise HTTPException(400, 'Unsupported OAuth authorization request.')
    state = data.get('state', '')
    if not isinstance(state, str) or len(state) > 2048:
        raise HTTPException(400, 'Invalid OAuth state.')
    return client, resource


def _form(params, client_name):
    # Chromium applies form-action to the 303 callback after the same-origin POST.
    # Only allow this registered callback's validated origin; path/query text must
    # never be interpolated into CSP. The form itself still posts only to us.
    callback_origin = redirect_origin(params.get('redirect_uri'))
    if callback_origin is None:
        raise HTTPException(400, 'Invalid OAuth redirect URI.')
    form_action = html.escape("'self' " + callback_origin, quote=True)
    fields = ''.join(f'<input type="hidden" name="{html.escape(k, quote=True)}" value="{html.escape(str(v), quote=True)}">'
                     for k, v in params.items() if k in {'client_id', 'redirect_uri', 'response_type',
                                                          'state', 'code_challenge', 'code_challenge_method',
                                                          'scope', 'resource'})
    # Deliberately do not embed any third-party branding or image URLs.
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; form-action {form_action}; base-uri 'none'">
    <title>Connect GPTmail</title><style>body{{background:#090f1f;color:#e9efff;font:16px system-ui;display:grid;place-items:center;min-height:90vh}}
    main{{width:min(420px,90vw);background:#151e32;border:1px solid #2d3a52;border-radius:20px;padding:30px}}
    input{{width:100%;padding:13px;box-sizing:border-box;border-radius:9px;background:#0d1528;border:1px solid #52617b;color:white}}
    button{{background:#6ba4ff;border:0;padding:14px 20px;border-radius:10px;font-weight:bold;width:100%;margin-top:20px}}
    small{{color:#a1abc0;line-height:1.6;display:block}}</style></head><body><main>
    <h1>GPTmail</h1><h2>Authorize {html.escape(client_name)}</h2>
    <p>This app wants to access your GPTmail MCP connection. Actual mail permissions are controlled in your GPTmail dashboard.</p>
    <form method="post" action="/oauth/authorize">{fields}
    <label>Owner password<br><input type="password" name="password" autocomplete="current-password" required autofocus></label>
    <p><label><input style="width:auto" type="checkbox" name="approve" value="yes" required> I authorize this MCP connection.</label></p>
    <button type="submit">Authorize connection</button></form>
    <p><small>The password remains on your server. GPTmail does not pass IMAP or SMTP credentials to the MCP client.</small></p>
    </main></body></html>'''


@router.get('/oauth/authorize', response_class=HTMLResponse)
def authorize_view(request: Request):
    params = dict(request.query_params)
    client, _ = _validate_auth_query(params)
    return HTMLResponse(_form(params, client['client_name']), headers={'Cache-Control': 'no-store',
                                                                       'X-Frame-Options': 'DENY'})


@router.post('/oauth/authorize')
async def authorize_submit(request: Request):
    rate_limit('consent', client_ip(request), max_count=20, window=900)
    values = parse_qs((await request.body()).decode('utf-8', 'replace'), keep_blank_values=True)
    data = {k: v[0] for k, v in values.items() if v}
    client, resource = _validate_auth_query(data)
    if data.get('approve') != 'yes' or not verify_password(data.get('password', '')):
        raise HTTPException(403, 'Authorization denied or password incorrect.')
    code = secrets.token_urlsafe(32)
    set_json('gptmail:oauth:code:' + token_hash(code), {
        'client_id': client['client_id'], 'redirect_uri': data['redirect_uri'],
        'code_challenge': data['code_challenge'], 'resource': resource,
    }, ttl=300)
    destination = data['redirect_uri']
    sep = '&' if '?' in destination else '?'
    destination += sep + urlencode({'code': code, 'state': data.get('state', ''), 'iss': base_url()})
    return RedirectResponse(destination, status_code=303, headers={'Cache-Control': 'no-store'})


def oauth_error(error, status=400):
    return JSONResponse({'error': error}, status_code=status, headers={'Cache-Control': 'no-store'})


def _valid_verifier(verifier, expected):
    if not isinstance(verifier, str) or not re.fullmatch(r'[A-Za-z0-9._~-]{43,128}', verifier):
        return False
    encoded = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode()
    return secrets.compare_digest(encoded, expected)


@router.post('/oauth/token')
async def token_exchange(request: Request):
    rate_limit('token', client_ip(request), max_count=120, window=3600)
    try:
        data = parse_qs((await request.body()).decode('utf-8'), keep_blank_values=True)
        args = {k: v[0] for k, v in data.items() if v}
        client_id = args.get('client_id', '')
        _client(client_id)
    except (UnicodeError, HTTPException):
        return oauth_error('invalid_client', status=401)
    kind = args.get('grant_type')
    if kind == 'authorization_code':
        raw_code = args.get('code', '')
        if not raw_code:
            return oauth_error('invalid_grant')
        details = pop_json('gptmail:oauth:code:' + token_hash(raw_code))
        if (not details or details['client_id'] != client_id
                or details['redirect_uri'] != args.get('redirect_uri')
                or not _valid_verifier(args.get('code_verifier', ''), details['code_challenge'])
                or (args.get('resource') and args.get('resource') != details['resource'])):
            return oauth_error('invalid_grant')
        resource = details['resource']
    elif kind == 'refresh_token':
        refresh = args.get('refresh_token', '')
        if not refresh:
            return oauth_error('invalid_grant')
        details = pop_json('gptmail:refresh:' + token_hash(refresh))
        if (not details or details['client_id'] != client_id
                or details['epoch'] != auth_epoch()
                or (args.get('resource') and args['resource'] != details['resource'])):
            return oauth_error('invalid_grant')
        resource = details['resource']
    else:
        return oauth_error('unsupported_grant_type')
    return JSONResponse(issue_tokens(client_id, resource), headers={'Cache-Control': 'no-store',
                                                                   'Pragma': 'no-cache'})
