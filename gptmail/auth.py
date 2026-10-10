"""Owner sessions, PBKDF-free scrypt password checks, OAuth bearer validation."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from .config import must_env, resource_url, base_url
from .store import redis_cmd, get_json, set_json


def make_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    if len(password) < 12:
        raise ValueError('Use an admin password of at least 12 characters.')
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f'{salt.hex()}:{digest.hex()}'


def verify_password(password: str) -> bool:
    try:
        salt_hex, expected_hex = must_env('ADMIN_PASSWORD_HASH').split(':', 1)
        expected = bytes.fromhex(expected_hex)
        derived = hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(salt_hex),
                                 n=2**14, r=8, p=1, dklen=len(expected))
        return hmac.compare_digest(derived, expected)
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def client_ip(request: Request) -> str:
    # Vercel-managed header; never accept X-Forwarded-For alone as trustworthy.
    ip = request.headers.get('x-vercel-forwarded-for', '').split(',')[0].strip()
    if not ip and request.client:
        ip = request.client.host
    return (ip or 'unknown')[:120]


def rate_limit(namespace: str, ip: str, *, max_count: int, window: int):
    # Hash IP addresses so the datastore does not persist raw IPs.
    key = f'gptmail:rate:{namespace}:{hashlib.sha256(ip.encode()).hexdigest()[:24]}'
    count = int(redis_cmd('INCR', key))
    if count == 1:
        redis_cmd('EXPIRE', key, window)
    if count > max_count:
        raise HTTPException(429, 'Too many requests; try later.')
    return key


def origin_check(request: Request):
    origin = request.headers.get('origin')
    if not origin:
        # CSRF requires a browser, where Origin is sent with same-site fetch POST.
        # Refuse missing Origin for the admin API, not OAuth token/MCP clients.
        raise HTTPException(403, 'Origin header required.')
    allowed = {base_url()}
    if not os.getenv('VERCEL'):
        allowed.update(('http://localhost:8000', 'http://127.0.0.1:8000'))
    if origin.rstrip('/') not in allowed:
        raise HTTPException(403, 'Cross-origin request blocked.')


def new_admin_session() -> str:
    secret = secrets.token_urlsafe(32)
    set_json('gptmail:session:' + token_hash(secret), {'created': datetime.now(timezone.utc).isoformat()}, ttl=8 * 3600)
    return secret


def admin_session(request: Request) -> str:
    secret = request.cookies.get('gptmail_session', '')
    if len(secret) < 32 or not get_json('gptmail:session:' + token_hash(secret)):
        raise HTTPException(401, 'Admin authentication required.')
    return secret


def logout(session: str):
    redis_cmd('DEL', 'gptmail:session:' + token_hash(session))


def auth_epoch():
    return int(redis_cmd('GET', 'gptmail:auth_epoch') or 0)


def revoke_all_connections():
    return redis_cmd('INCR', 'gptmail:auth_epoch')


def issue_tokens(client_id: str, resource: str):
    access = secrets.token_urlsafe(32)
    refresh = secrets.token_urlsafe(40)
    epoch = auth_epoch()
    details = {'client_id': client_id, 'resource': resource, 'epoch': epoch}
    set_json('gptmail:access:' + token_hash(access), details, ttl=3600)
    set_json('gptmail:refresh:' + token_hash(refresh), details, ttl=30 * 86400)
    return {'access_token': access, 'token_type': 'Bearer', 'expires_in': 3600,
            'refresh_token': refresh, 'scope': 'mail'}


def verify_bearer(request: Request):
    header = request.headers.get('authorization', '')
    if not header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Authentication required', headers={
            'WWW-Authenticate': f'Bearer resource_metadata="{base_url()}/.well-known/oauth-protected-resource", scope="mail"'
        })
    token = header[7:]
    details = get_json('gptmail:access:' + token_hash(token))
    if (not details or details.get('epoch') != auth_epoch()
            or details.get('resource') not in (resource_url(), base_url())):
        raise HTTPException(status_code=401, detail='Invalid or expired token', headers={
            'WWW-Authenticate': f'Bearer resource_metadata="{base_url()}/.well-known/oauth-protected-resource", scope="mail"'
        })
    return details


def validate_redirect(uri):
    if not isinstance(uri, str) or len(uri) > 1500 or '\n' in uri or '\r' in uri:
        return False
    try:
        parsed = urlsplit(uri)
        return (not parsed.fragment and not parsed.username and not parsed.password
                and ((parsed.scheme == 'https' and bool(parsed.hostname)) or
                     (not os.getenv('VERCEL') and parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'))))
    except ValueError:
        return False
