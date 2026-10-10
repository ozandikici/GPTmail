"""Owner-initiated Google/Microsoft mailbox OAuth, separate from ChatGPT OAuth.

Provider tokens and one-use PKCE state are encrypted in Redis. They are never
returned to the browser or MCP client. No mail-provider registration is implied
by configuring this application: the operator must supply their Web app credentials.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as URLRequest, HTTPRedirectHandler, build_opener

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .auth import admin_session, origin_check, rate_limit, token_hash
from .config import base_url, ConfigurationError
from . import store

router = APIRouter()
FLOW_COOKIE = 'gptmail_provider_flow'
FLOW_TTL = 600
SPECS = {
    'google': {
        'name': 'Gmail / Google Workspace',
        'client_id_env': 'GOOGLE_CLIENT_ID', 'client_secret_env': 'GOOGLE_CLIENT_SECRET',
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scopes': ['https://mail.google.com/'],
        'imap_host': 'imap.gmail.com', 'imap_port': 993,
        'smtp_host': 'smtp.gmail.com', 'smtp_port': 465,
        'notes': ['A Google Web OAuth application and consent configuration are required.',
                  'Google mail access is a restricted scope; verification or testing limits may apply.',
                  'Google Testing refresh tokens for mail access usually expire after seven days.'],
    },
    'microsoft': {
        'name': 'Outlook / Microsoft 365',
        'client_id_env': 'MICROSOFT_CLIENT_ID', 'client_secret_env': 'MICROSOFT_CLIENT_SECRET',
        'scopes': ['https://outlook.office.com/IMAP.AccessAsUser.All',
                   'https://outlook.office.com/SMTP.Send', 'offline_access'],
        'imap_host': 'outlook.office365.com', 'imap_port': 993,
        'smtp_host': 'smtp.office365.com', 'smtp_port': 587,
        'smtp_hosts': ['smtp.office365.com', 'smtp-mail.outlook.com'],
        'notes': ['An Entra Web application supporting the intended account types is required.',
                  'IMAP and SMTP AUTH must be allowed by the mailbox and tenant policy.',
                  'A successful Microsoft sign-in does not override tenant restrictions.'],
    },
}


class ProviderError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def callback_url(provider):
    return base_url() + f'/oauth/mail/{provider}/callback'


def _tenant():
    tenant = os.getenv('MICROSOFT_TENANT_ID', 'common').strip() or 'common'
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', tenant):
        raise ConfigurationError('MICROSOFT_TENANT_ID must be a tenant ID, verified domain, common, organizations, or consumers.')
    return tenant


def provider_status():
    result = []
    for provider, spec in SPECS.items():
        missing = [name for name in (spec['client_id_env'], spec['client_secret_env'])
                   if not os.getenv(name, '').strip()]
        if provider == 'microsoft':
            try:
                _tenant()
            except ConfigurationError:
                missing.append('MICROSOFT_TENANT_ID')
        result.append({'id': provider, 'name': spec['name'], 'auth_type': 'oauth',
                       'configured': not missing, 'status': 'setup_required' if missing else 'ready',
                       'missing_env': missing, 'redirect_uri': callback_url(provider),
                       'notes': spec['notes']})
    result.append({'id': 'imap', 'name': 'Other IMAP / SMTP provider', 'auth_type': 'password',
                   'configured': True, 'status': 'ready', 'missing_env': [], 'redirect_uri': None,
                   'notes': ['Requires publicly reachable IMAP over TLS and, optionally, SMTP over TLS or STARTTLS.',
                             'Use the provider-supported password or app password only in this private dashboard.',
                             'Proton Mail Bridge is local; Tuta does not offer standard IMAP access. Neither connects directly to this Vercel server.']})
    return result


def _config(provider):
    if provider not in SPECS:
        raise HTTPException(404, 'Unknown mail provider.')
    status = next(item for item in provider_status() if item['id'] == provider)
    if not status['configured']:
        raise HTTPException(503, detail={'code': 'setup_required', 'provider': provider,
                                        'missing_env': status['missing_env']})
    spec = dict(SPECS[provider])
    spec['client_id'] = os.environ[spec['client_id_env']].strip()
    spec['client_secret'] = os.environ[spec['client_secret_env']].strip()
    if provider == 'microsoft':
        prefix = 'https://login.microsoftonline.com/' + _tenant() + '/oauth2/v2.0/'
        spec.update(authorize_url=prefix + 'authorize', token_url=prefix + 'token')
    return spec


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _token_request(spec, fields):
    # Fixed provider endpoints; refuse redirects so client credentials cannot be
    # forwarded to another origin. Never expose provider response bodies/errors.
    request = URLRequest(spec['token_url'], data=urlencode({
        'client_id': spec['client_id'], 'client_secret': spec['client_secret'], **fields}).encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'},
        method='POST')
    try:
        with build_opener(_NoRedirect()).open(request, timeout=15) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError
        result = json.loads(raw)
        if not isinstance(result, dict) or result.get('error'):
            raise ValueError
        return result
    except HTTPError as exc:
        # Only inspect a fixed machine-readable error code, never log descriptions.
        error = ''
        try:
            value = json.loads(exc.read(65536))
            error = value.get('error', '') if isinstance(value, dict) else ''
        except (ValueError, OSError):
            pass
        finally:
            exc.close()
        if error in ('invalid_grant', 'interaction_required', 'consent_required'):
            raise ProviderError('reconnect_required', 'Mail provider authorization expired or was revoked. Reconnect this account.') from None
        raise ProviderError('provider_unavailable', 'Mail provider token exchange failed. Check the provider application configuration and try again.') from None
    except (OSError, URLError, ValueError):
        raise ProviderError('provider_unavailable', 'Mail provider token exchange failed. Try again later.') from None


def _tokens(result, provider, old=None):
    access = result.get('access_token')
    refresh = result.get('refresh_token') or (old or {}).get('refresh_token')
    for value in (access, refresh):
        if not isinstance(value, str) or not value or len(value) > 20000 or re.search(r'[\x00-\x20\x7f]', value):
            raise ProviderError('reconnect_required', 'Offline mail access was not granted. Reconnect and approve offline access.')
    if str(result.get('token_type', '')).lower() != 'bearer':
        raise ProviderError('provider_unavailable', 'The provider returned an unsupported token type.')
    try:
        lifetime = int(result['expires_in'])
        if not 1 <= lifetime <= 7 * 86400:
            raise ValueError
    except (KeyError, ValueError, TypeError):
        raise ProviderError('provider_unavailable', 'The provider returned an invalid token lifetime.') from None
    return {'provider': provider, 'access_token': access, 'refresh_token': refresh,
            'expires_at': time.time() + lifetime}


def oauth_access_token(account):
    provider = account.get('provider')
    spec = SPECS.get(provider)
    if not spec or account.get('auth_type') != 'oauth':
        raise ProviderError('reconnect_required', 'Unknown OAuth mail provider. Reconnect this account.')
    # OAuth credentials must never be sent to user-configured mail servers.
    if (any(account.get(field) != spec[field] for field in ('imap_host', 'imap_port', 'smtp_port'))
            or account.get('smtp_host') not in spec.get('smtp_hosts', [spec['smtp_host']])):
        raise ProviderError('reconnect_required', 'OAuth mailbox endpoints do not match this provider. Reconnect this account.')
    if account.get('_oauth_access_token'):
        return account['_oauth_access_token']  # Callback-only token, never persisted.
    account_id = account.get('id', '')
    blob, tokens = store.oauth_token_record(account_id)
    if not tokens or tokens.get('provider') != provider:
        raise ProviderError('reconnect_required', 'Mail provider authorization is missing. Reconnect this account.')
    if tokens.get('expires_at', 0) > time.time() + 60:
        return tokens['access_token']
    try:
        config = _config(provider)
        fields = {'grant_type': 'refresh_token', 'refresh_token': tokens['refresh_token']}
        if provider == 'microsoft':
            fields['scope'] = ' '.join(config['scopes'])
        renewed = _tokens(_token_request(config, fields), provider, tokens)
    except HTTPException:
        raise ProviderError('setup_required', 'Mail provider OAuth configuration is missing. Ask the owner to complete provider setup.') from None
    except ProviderError as exc:
        current_blob, current = store.oauth_token_record(account_id)
        if current_blob != blob and current and current.get('expires_at', 0) > time.time() + 60:
            return current['access_token']
        if exc.code == 'reconnect_required':
            store.update_account_fields(account_id, {'connection_status': 'reconnect_required'})
        raise
    if store.replace_oauth_tokens(account_id, blob, renewed):
        store.update_account_fields(account_id, {'connection_status': 'connected'})
        return renewed['access_token']
    _, current = store.oauth_token_record(account_id)
    if current and current.get('expires_at', 0) > time.time() + 60:
        return current['access_token']
    raise ProviderError('reconnect_required', 'This account was removed or changed. Reconnect if necessary.')


def xoauth2_payload(account):
    username = account.get('username', '')
    if not isinstance(username, str) or not username or re.search(r'[\x00-\x20\x7f]', username):
        raise ProviderError('reconnect_required', 'Invalid OAuth mailbox username. Reconnect this account.')
    token = oauth_access_token(account)
    return f'user={username}\x01auth=Bearer {token}\x01\x01'


def test_oauth_smtp(account):
    """Verify only fixed provider endpoints, supporting Outlook.com and M365."""
    from . import mail
    spec = SPECS[account['provider']]
    original = account['smtp_host']
    for host in dict.fromkeys([original, *spec.get('smtp_hosts', [spec['smtp_host']])]):
        account['smtp_host'] = host
        try:
            if mail.test_smtp(account):
                return True
        except mail.MailError:
            pass
    account['smtp_host'] = original
    return False


@router.get('/api/admin/providers')
def providers_view(request: Request):
    admin_session(request)
    return {'providers': provider_status()}


@router.post('/api/admin/providers/{provider}/connect')
async def connect_provider(provider: str, request: Request):
    from .mail import safe_address
    origin_check(request)
    session = admin_session(request)
    spec = _config(provider)
    rate_limit('provider_connect', token_hash(session), max_count=12, window=900)
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError
        email = data.get('email', '').strip()
        if safe_address(email) != email or re.search(r'[\x00-\x20\x7f]', email):
            raise ValueError
        name = data.get('name', '').strip() or email
        if len(name) > 80:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, 'Enter a valid mailbox email and a name of at most 80 characters.') from None
    account_id = None
    for account in store.accounts_public():
        if (account.get('auth_type') == 'oauth' and account.get('provider') == provider
                and account.get('email', '').casefold() == email.casefold()):
            account_id = account['id']
            break
    state = secrets.token_urlsafe(32)
    browser_secret = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    flow = {'provider': provider, 'email': email, 'name': name, 'account_id': account_id,
            'session_hash': token_hash(session), 'browser_hash': token_hash(browser_secret),
            'verifier': verifier}
    store.redis_cmd('SET', 'gptmail:provider_flow:' + token_hash(state), store.encrypt_json(flow), 'EX', FLOW_TTL)
    params = {'client_id': spec['client_id'], 'redirect_uri': callback_url(provider),
              'response_type': 'code', 'scope': ' '.join(spec['scopes']), 'state': state,
              'code_challenge': challenge, 'code_challenge_method': 'S256', 'login_hint': email}
    if provider == 'google':
        params.update(access_type='offline', prompt='consent')
    else:
        params.update(response_mode='query', prompt='select_account')
    response = JSONResponse({'ok': True, 'authorization_url': spec['authorize_url'] + '?' + urlencode(params)},
                            headers={'Cache-Control': 'no-store'})
    # The owner session stays SameSite=Strict; only this short-lived correlation
    # cookie is Lax so the provider's top-level GET callback can carry it.
    response.set_cookie(FLOW_COOKIE, browser_secret, max_age=FLOW_TTL, httponly=True,
                        secure=base_url().startswith('https://'), samesite='lax', path='/oauth/mail/')
    return response


def _finish(provider, *, error=None):
    params = {'provider_error': error, 'provider': provider} if error else {'provider_connected': provider}
    response = RedirectResponse(base_url() + '/?' + urlencode(params), status_code=303,
                                headers={'Cache-Control': 'no-store'})
    response.delete_cookie(FLOW_COOKIE, path='/oauth/mail/')
    return response


@router.get('/oauth/mail/{provider}/callback')
def provider_callback(provider: str, request: Request):
    from . import mail
    if provider not in SPECS:
        raise HTTPException(404, 'Unknown mail provider.')
    state = request.query_params.get('state', '')
    browser_secret = request.cookies.get(FLOW_COOKIE, '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', state) or not browser_secret:
        return _finish(provider, error='state_invalid')
    key = 'gptmail:provider_flow:' + token_hash(state)
    blob = store.redis_cmd('GET', key)
    if not blob:
        return _finish(provider, error='state_invalid')
    flow = store.decrypt_json(blob)
    if (flow.get('provider') != provider or not secrets.compare_digest(
            flow.get('browser_hash', ''), token_hash(browser_secret))):
        return _finish(provider, error='state_invalid')
    if store.redis_cmd('GETDEL', key) != blob:
        return _finish(provider, error='state_invalid')
    if not store.get_json('gptmail:session:' + flow['session_hash']):
        return _finish(provider, error='session_expired')
    if request.query_params.get('error'):
        return _finish(provider, error='cancelled' if request.query_params['error'] == 'access_denied' else 'authorization_failed')
    code = request.query_params.get('code', '')
    if not code or len(code) > 12000:
        return _finish(provider, error='authorization_failed')
    try:
        spec = _config(provider)
        tokens = _tokens(_token_request(spec, {'grant_type': 'authorization_code', 'code': code,
            'redirect_uri': callback_url(provider), 'code_verifier': flow['verifier']}), provider)
        account = {'id': flow['account_id'] or secrets.token_hex(9), 'name': flow['name'],
                   'email': flow['email'], 'username': flow['email'], 'smtp_username': flow['email'],
                   'auth_type': 'oauth', 'provider': provider, 'enabled': True, 'mcp_enabled': True,
                   'connection_status': 'connected', 'smtp_status': 'connected',
                   **{field: spec[field] for field in ('imap_host', 'imap_port', 'smtp_host', 'smtp_port')}}
        account['_oauth_access_token'] = tokens['access_token']
        if not mail.test_imap(account):
            raise mail.MailError('IMAP mailbox access was not confirmed.')
        if not test_oauth_smtp(account):
            account['smtp_status'] = 'unavailable'
        account.pop('_oauth_access_token', None)
        for _ in range(3):
            old_blob, old = store.account_record(account['id'])
            if flow['account_id'] and not old:
                return _finish(provider, error='account_removed')
            if old:
                account['mcp_enabled'] = old.get('mcp_enabled', True)
                account['enabled'] = old.get('enabled', True)
            if store.save_oauth_account(account, tokens, old_blob):
                break
        else:
            return _finish(provider, error='account_changed')
        store.audit('provider_connected', account_id=account['id'], source=provider)
        return _finish(provider)
    except HTTPException as exc:
        if exc.status_code == 503:
            return _finish(provider, error='setup_required')
        raise
    except ProviderError as exc:
        return _finish(provider, error=exc.code)
    except mail.MailError:
        return _finish(provider, error='mailbox_auth_failed')
