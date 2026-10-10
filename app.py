"""GPTmail: single-owner open-source IMAP/SMTP + authenticated remote MCP."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from gptmail import mail
from gptmail.auth import (admin_session, new_admin_session, logout, verify_password,
                          origin_check, client_ip, rate_limit, revoke_all_connections)
from gptmail.config import (base_url, resource_url, DEFAULT_PERMISSIONS,
                            PERMISSION_LABELS, ConfigurationError)
from gptmail.store import (save_account, remove_account, get_account, accounts_public,
                            permissions, save_permissions, recent_audit, audit,
                            pending_list, pending_consume, pending_reject, update_account_fields)
from gptmail.oauth import router as oauth_router
from gptmail.mcp import router as mcp_router
from gptmail.providers import router as provider_router, provider_status, test_oauth_smtp

ROOT = Path(__file__).resolve().parent
app = FastAPI(title='GPTmail', docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(oauth_router)
app.include_router(mcp_router)
app.include_router(provider_router)
app.mount('/static', StaticFiles(directory=str(ROOT / 'static')), name='static')


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if request.url.path in ('/', '/static/app.css', '/static/app.js'):
        response.headers['Content-Security-Policy'] = ("default-src 'self'; script-src 'self'; style-src 'self'; "
                                                     "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
                                                     "frame-ancestors 'none'; form-action 'self'; base-uri 'none'")
    return response


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(ROOT / 'static' / 'index.html', media_type='text/html',
                        headers={'Cache-Control': 'no-store'})


@app.get('/robots.txt', include_in_schema=False)
def robots():
    return Response('User-agent: *\nDisallow: /\n', media_type='text/plain')


@app.get('/health')
def health():
    return {'service': 'GPTmail', 'healthy': True, 'version': '1.0.0'}


@app.post('/api/auth/login')
async def login(request: Request):
    origin_check(request)
    rate_limit('admin_login', client_ip(request), max_count=12, window=900)
    payload = await request.json()
    password = payload.get('password', '') if isinstance(payload, dict) else ''
    if not isinstance(password, str) or not verify_password(password):
        raise HTTPException(401, 'Password incorrect.')
    secret = new_admin_session()
    response = JSONResponse({'authenticated': True})
    response.set_cookie('gptmail_session', secret, max_age=8 * 3600,
                        secure=base_url().startswith('https://'), httponly=True,
                        samesite='strict', path='/')
    audit('admin_login', source='dashboard')
    return response


@app.post('/api/auth/logout')
def signout(request: Request):
    origin_check(request)
    secret = admin_session(request)
    logout(secret)
    response = JSONResponse({'authenticated': False})
    response.delete_cookie('gptmail_session', path='/')
    return response


@app.get('/api/admin/state')
def admin_state(request: Request):
    admin_session(request)
    return {
        'accounts': accounts_public(), 'permissions': permissions(),
        'permission_labels': PERMISSION_LABELS,
        'pending': pending_list(), 'audit': recent_audit(),
        'mcp_url': resource_url(),
        'has_accounts': bool(accounts_public()),
        'providers': provider_status(),
    }


def _account(data):
    record = get_account(data.get('account_id', ''))
    if not record:
        raise HTTPException(404, 'Unknown account.')
    return record


def _approve(pending_id):
    item = pending_consume(pending_id)
    if not item:
        raise HTTPException(404, 'Approval request has expired or was already handled.')
    account = get_account(item['account_id'])
    if not account:
        raise HTTPException(404, 'Account was removed.')
    if not account.get('mcp_enabled', True):
        raise HTTPException(403, 'MCP access was disabled for this account.')
    setting = permissions()
    if item['action'] == 'send':
        if not setting.get(item.get('source_permission', 'send'), False):
            raise HTTPException(403, 'The original outgoing MCP permission was disabled.')
        rate_limit('outgoing_' + account['id'], account['id'], max_count=40, window=3600)
        result = mail.send_email(account, item['message'])
    elif item['action'] == 'delete':
        if not setting['delete']:
            raise HTTPException(403, 'Delete MCP permission was disabled.')
        result = mail.delete_email(account, item['uid'], item['folder'])
    else:
        raise HTTPException(400, 'Unsupported pending action.')
    audit('approval_executed_' + item['action'], account_id=account['id'])
    return result


@app.post('/api/admin/action')
async def admin_action(request: Request):
    origin_check(request)
    admin_session(request)
    payload = await request.json()
    if not isinstance(payload, dict) or len(str(payload)) > 300_000:
        raise HTTPException(400, 'Invalid request.')
    action = payload.get('action')
    data = payload.get('data', {})
    if not isinstance(data, dict):
        raise HTTPException(400, 'Invalid data.')
    try:
        if action == 'account/add':
            account = mail.validated_account(data)
            mail.test_imap(account)  # never save an unverified IMAP password
            if account.get('smtp_host'):
                mail.test_smtp(account)
            account_id = save_account(account)
            audit('account_added', account_id=account_id)
            result = {'id': account_id, 'saved': True}
        elif action == 'account/update':
            old = _account(data)
            if old.get('auth_type') == 'oauth':
                if any(field not in ('account_id', 'name') for field in data):
                    raise HTTPException(400, 'OAuth mailbox endpoints and identity cannot be edited. Reconnect through the provider instead.')
                name = data.get('name', old['name'])
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
                    raise HTTPException(400, 'Account name must contain 1-80 characters.')
                if not update_account_fields(old['id'], {'name': name.strip()}):
                    raise HTTPException(409, 'Account changed; refresh and try again.')
                audit('account_updated', account_id=old['id'])
                return {'ok': True, 'data': {'id': old['id'], 'saved': True}}
            allowed = ('name', 'email', 'username', 'password', 'imap_host', 'imap_port',
                       'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password')
            updated = dict(old)
            for field in allowed:
                if field in data and not (field in ('password', 'smtp_password') and not data[field]):
                    updated[field] = data[field]
            account = mail.validated_account(updated)
            account['id'] = old['id']
            account['mcp_enabled'] = old.get('mcp_enabled', True)
            mail.test_imap(account)
            if account.get('smtp_host'):
                mail.test_smtp(account)
            save_account(account)
            audit('account_updated', account_id=account['id'])
            result = {'id': account['id'], 'saved': True}
        elif action == 'account/access':
            account = _account(data)
            if not isinstance(data.get('mcp_enabled'), bool):
                raise HTTPException(400, 'mcp_enabled must be a boolean.')
            account['mcp_enabled'] = data['mcp_enabled']
            save_account(account)
            audit('account_mcp_access_changed', account_id=account['id'])
            result = {'mcp_enabled': account['mcp_enabled']}
        elif action == 'account/remove':
            account = _account(data)
            remove_account(account['id'])
            audit('account_removed', account_id=account['id'])
            result = {'removed': True}
        elif action == 'account/test':
            account = _account(data)
            imap_ok = mail.test_imap(account)
            if account.get('auth_type') == 'oauth':
                smtp_ok = test_oauth_smtp(account)
                update_account_fields(account['id'], {'connection_status': 'connected',
                    'smtp_status': 'connected' if smtp_ok else 'unavailable', 'smtp_host': account['smtp_host']})
                result = {'imap': imap_ok, 'smtp': smtp_ok}
            else:
                result = {'imap': imap_ok,
                          'smtp': mail.test_smtp(account) if account.get('smtp_host') else None}
        elif action == 'permissions/update':
            result = save_permissions(data)
        elif action == 'approval/approve':
            result = _approve(data.get('id', ''))
        elif action == 'approval/reject':
            result = {'rejected': pending_reject(data.get('id', ''))}
        elif action == 'connections/revoke':
            revoke_all_connections()
            audit('oauth_tokens_revoked')
            result = {'revoked': True}
        elif action == 'mail/folders':
            result = mail.list_folders(_account(data))
        elif action == 'mail/list':
            result = mail.list_messages(_account(data), data.get('folder', 'INBOX'), data.get('limit', 30))
        elif action == 'mail/search':
            result = mail.search_messages(_account(data), data.get('query', ''),
                                          data.get('folder', 'INBOX'), data.get('limit', 30))
        elif action == 'mail/read':
            result = mail.read_message(_account(data), data.get('uid'), data.get('folder', 'INBOX'))
        elif action == 'mail/send':
            account = _account(data)
            rate_limit('owner_send_' + account['id'], account['id'], max_count=40, window=3600)
            result = mail.send_email(account, data)
            audit('dashboard_sent_email', account_id=account['id'])
        elif action == 'mail/mark':
            account = _account(data)
            result = mail.set_flag(account, data.get('uid'), data.get('flag'),
                                   data.get('enabled'), data.get('folder', 'INBOX'))
        elif action == 'mail/move':
            account = _account(data)
            result = mail.move_email(account, data.get('uid'), data.get('destination'), data.get('folder', 'INBOX'))
            audit('dashboard_move_message', account_id=account['id'])
        elif action == 'mail/delete':
            account = _account(data)
            result = mail.delete_email(account, data.get('uid'), data.get('folder', 'INBOX'))
            audit('dashboard_trash_message', account_id=account['id'])
        else:
            raise HTTPException(400, 'Unknown action.')
    except mail.MailError as exc:
        raise HTTPException(400, str(exc)) from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(400, 'Invalid or missing form field.') from exc
    return {'ok': True, 'data': result}


@app.exception_handler(ConfigurationError)
async def config_handler(request: Request, exc: ConfigurationError):
    return JSONResponse({'detail': str(exc)}, status_code=503)
