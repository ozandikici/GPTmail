"""Upstash REST storage and encrypted per-account secrets.

Vercel's filesystem is ephemeral. This deliberately refuses to use local files
for production secrets. All mail account records and pending outbound drafts
are encrypted before being written to the database.
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from cryptography.fernet import Fernet, InvalidToken

from .config import ConfigurationError, DEFAULT_PERMISSIONS, must_env


class RedisError(RuntimeError):
    pass


def redis_cmd(*args):
    url = must_env('UPSTASH_REDIS_REST_URL').rstrip('/')
    token = must_env('UPSTASH_REDIS_REST_TOKEN')
    if not url.startswith('https://'):
        raise ConfigurationError('UPSTASH_REDIS_REST_URL must use HTTPS.')
    body = json.dumps(list(args), ensure_ascii=False).encode('utf-8')
    req = Request(url, data=body, method='POST', headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'GPTmail/1.0',
    })
    try:
        with urlopen(req, timeout=10) as response:
            result = json.load(response)
    except Exception as exc:
        raise RedisError('Secure database request failed.') from exc
    if not isinstance(result, dict) or result.get('error'):
        raise RedisError('Database rejected the operation.')
    return result.get('result')


def set_json(key, value, ttl=None, *, only_new=False):
    args = ['SET', key, json.dumps(value, ensure_ascii=False, separators=(',', ':'))]
    if ttl:
        args += ['EX', int(ttl)]
    if only_new:
        args.append('NX')
    return redis_cmd(*args)


def get_json(key, default=None):
    raw = redis_cmd('GET', key)
    return json.loads(raw) if raw is not None else default


def pop_json(key):
    raw = redis_cmd('GETDEL', key)
    return json.loads(raw) if raw is not None else None


def cipher():
    try:
        return Fernet(must_env('DATA_ENCRYPTION_KEY').encode('ascii'))
    except (ValueError, InvalidToken) as exc:
        raise ConfigurationError('DATA_ENCRYPTION_KEY must be a valid Fernet key.') from exc


def encrypt_json(data):
    return cipher().encrypt(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('ascii')


def decrypt_json(token):
    try:
        return json.loads(cipher().decrypt(token.encode('ascii')))
    except InvalidToken as exc:
        raise RedisError('Could not decrypt stored credentials. Verify DATA_ENCRYPTION_KEY.') from exc


def accounts_public():
    records = []
    for account_id in (redis_cmd('SMEMBERS', 'gptmail:account_ids') or []):
        account = get_account(account_id)
        if account:
            # An allowlist keeps future token/secret fields out of dashboard and MCP responses.
            public_fields = {'id', 'name', 'email', 'username', 'imap_host', 'imap_port',
                             'smtp_host', 'smtp_port', 'smtp_username', 'enabled', 'mcp_enabled',
                             'auth_type', 'provider', 'connection_status', 'smtp_status'}
            records.append({k: v for k, v in account.items() if k in public_fields})
    return sorted(records, key=lambda a: a.get('name', '').lower())


def account_record(account_id):
    if not isinstance(account_id, str) or not account_id or len(account_id) > 64:
        raise ValueError('Invalid account ID.')
    blob = redis_cmd('GET', f'gptmail:account:{account_id}')
    return blob, decrypt_json(blob) if blob else None


def get_account(account_id):
    return account_record(account_id)[1]


def save_account(account):
    account_id = account.get('id') or secrets.token_hex(9)
    account['id'] = account_id
    redis_cmd('SET', f'gptmail:account:{account_id}', encrypt_json(account))
    redis_cmd('SADD', 'gptmail:account_ids', account_id)
    return account_id


def remove_account(account_id):
    redis_cmd('DEL', f'gptmail:account:{account_id}')
    redis_cmd('DEL', f'gptmail:provider_tokens:{account_id}')
    redis_cmd('SREM', 'gptmail:account_ids', account_id)


# Compare encrypted records atomically so a refresh cannot restore a removed account
# or overwrite newer tokens from another Vercel instance.
OAUTH_ACCOUNT_CAS = '''-- gptmail:oauth_account_cas
local current = redis.call('GET', KEYS[1])
if (ARGV[1] == '' and current) or (ARGV[1] ~= '' and current ~= ARGV[1]) then return 0 end
redis.call('SET', KEYS[1], ARGV[2])
redis.call('SET', KEYS[2], ARGV[3])
redis.call('SADD', KEYS[3], ARGV[4])
return 1'''

OAUTH_TOKEN_CAS = '''-- gptmail:oauth_token_cas
if redis.call('EXISTS', KEYS[1]) == 0 or redis.call('GET', KEYS[2]) ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[2], ARGV[2])
return 1'''

ACCOUNT_FIELDS_CAS = '''-- gptmail:account_fields_cas
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[1], ARGV[2])
return 1'''


def save_oauth_account(account, tokens, expected_blob=None):
    account_id = account['id']
    return bool(redis_cmd('EVAL', OAUTH_ACCOUNT_CAS, 3, f'gptmail:account:{account_id}',
                         f'gptmail:provider_tokens:{account_id}', 'gptmail:account_ids',
                         expected_blob or '', encrypt_json(account), encrypt_json(tokens), account_id))


def oauth_token_record(account_id):
    blob = redis_cmd('GET', f'gptmail:provider_tokens:{account_id}')
    return blob, decrypt_json(blob) if blob else None


def replace_oauth_tokens(account_id, expected_blob, tokens):
    return bool(redis_cmd('EVAL', OAUTH_TOKEN_CAS, 2, f'gptmail:account:{account_id}',
                         f'gptmail:provider_tokens:{account_id}', expected_blob, encrypt_json(tokens)))


def update_account_fields(account_id, changes):
    for _ in range(3):
        blob, account = account_record(account_id)
        if not account:
            return False
        account.update(changes)
        if redis_cmd('EVAL', ACCOUNT_FIELDS_CAS, 1, f'gptmail:account:{account_id}', blob, encrypt_json(account)):
            return True
    return False


def permissions():
    configured = get_json('gptmail:permissions', {})
    return {**DEFAULT_PERMISSIONS, **{k: bool(v) for k, v in configured.items() if k in DEFAULT_PERMISSIONS}}


def save_permissions(changes):
    if not isinstance(changes, dict) or not changes or any(k not in DEFAULT_PERMISSIONS or not isinstance(v, bool) for k, v in changes.items()):
        raise ValueError('Invalid permissions payload.')
    merged = {**permissions(), **changes}
    set_json('gptmail:permissions', merged)
    audit('settings_changed', fields=sorted(changes.keys()))
    return merged


def audit(action, *, account_id=None, status='ok', **meta):
    # NEVER write mail content, recipients, passwords, access tokens or subjects.
    item = {'at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'action': str(action)[:70], 'status': status}
    if account_id:
        item['account_id'] = str(account_id)[:64]
    for field in ('fields', 'permission', 'source'):
        if field in meta:
            item[field] = meta[field]
    try:
        redis_cmd('LPUSH', 'gptmail:audit', json.dumps(item, ensure_ascii=False))
        redis_cmd('LTRIM', 'gptmail:audit', 0, 99)
    except (RedisError, ConfigurationError):
        pass  # A logging outage must not convert a completed send into a retry.


def recent_audit():
    return [json.loads(row) for row in (redis_cmd('LRANGE', 'gptmail:audit', 0, 79) or [])]


def pending_create(action, payload):
    pending_id = secrets.token_hex(12)
    record = {'id': pending_id, 'action': action,
              'created_at': datetime.now(timezone.utc).isoformat(), **payload}
    redis_cmd('SET', f'gptmail:pending:{pending_id}', encrypt_json(record), 'EX', 7 * 86400)
    redis_cmd('SADD', 'gptmail:pending_ids', pending_id)
    return pending_id


def pending_list():
    records = []
    for pending_id in (redis_cmd('SMEMBERS', 'gptmail:pending_ids') or []):
        blob = redis_cmd('GET', f'gptmail:pending:{pending_id}')
        if not blob:
            redis_cmd('SREM', 'gptmail:pending_ids', pending_id)
            continue
        item = decrypt_json(blob)
        # Payload is visible only to the authenticated dashboard owner.
        records.append(item)
    return sorted(records, key=lambda a: a.get('created_at', ''), reverse=True)


def pending_consume(pending_id):
    if not isinstance(pending_id, str) or len(pending_id) != 24:
        raise ValueError('Invalid pending ID.')
    blob = redis_cmd('GETDEL', f'gptmail:pending:{pending_id}')
    redis_cmd('SREM', 'gptmail:pending_ids', pending_id)
    return decrypt_json(blob) if blob else None


def pending_reject(pending_id):
    item = pending_consume(pending_id)
    if item:
        audit('approval_rejected', account_id=item.get('account_id'))
    return item is not None
