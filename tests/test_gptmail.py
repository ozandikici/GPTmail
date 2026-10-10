"""Offline tests: OAuth, owner authentication and default-deny MCP rights."""
from __future__ import annotations

import base64
import hashlib
import json
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from gptmail.auth import make_hash
from gptmail.mail import encode_folder, decode_folder, MailError, validate_message


class MemoryRedis:
    def __init__(self):
        self.data = {}

    def __call__(self, *args):
        action, *params = args
        action = action.upper()
        k = params[0]
        if action == 'EVAL':
            count = int(params[1])
            keys, values = params[2:2 + count], params[2 + count:]
            if k.startswith('-- gptmail:oauth_account_cas'):
                old, new_account, new_tokens, account_id = values
                current = self.data.get(keys[0])
                if (not old and current is not None) or (old and current != old): return 0
                self.data[keys[0]], self.data[keys[1]] = new_account, new_tokens
                self.data.setdefault(keys[2], set()).add(account_id)
                return 1
            if k.startswith('-- gptmail:oauth_token_cas'):
                if keys[0] not in self.data or self.data.get(keys[1]) != values[0]: return 0
                self.data[keys[1]] = values[1]
                return 1
            if k.startswith('-- gptmail:account_fields_cas'):
                if self.data.get(keys[0]) != values[0]: return 0
                self.data[keys[0]] = values[1]
                return 1
            raise AssertionError('Unsupported fake Redis script')
        if action == 'GET': return self.data.get(k)
        if action == 'GETDEL': return self.data.pop(k, None)
        if action == 'DEL':
            value = int(k in self.data); self.data.pop(k, None); return value
        if action == 'SET':
            if 'NX' in params and k in self.data: return None
            self.data[k] = params[1]; return 'OK'
        if action == 'SADD':
            self.data.setdefault(k, set()).add(params[1]); return 1
        if action == 'SREM':
            self.data.setdefault(k, set()).discard(params[1]); return 1
        if action == 'SMEMBERS': return list(self.data.get(k, set()))
        if action == 'INCR':
            self.data[k] = int(self.data.get(k, 0)) + 1; return self.data[k]
        if action == 'EXPIRE': return 1
        if action == 'LPUSH':
            self.data.setdefault(k, []).insert(0, params[1]); return len(self.data[k])
        if action == 'LTRIM':
            self.data[k] = self.data.get(k, [])[int(params[1]):int(params[2])+1]; return 'OK'
        if action == 'LRANGE': return self.data.get(k, [])[int(params[1]):int(params[2])+1]
        raise AssertionError(f'Unsupported fake redis command: {args}')


@pytest.fixture
def client(monkeypatch):
    import gptmail.store as store
    import gptmail.auth as auth
    from app import app
    fake = MemoryRedis()
    monkeypatch.setattr(store, 'redis_cmd', fake)
    monkeypatch.setattr(auth, 'redis_cmd', fake)
    monkeypatch.setenv('APP_BASE_URL', 'http://localhost:8000')
    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.setenv('ADMIN_PASSWORD_HASH', make_hash('test-password-strong-123'))
    monkeypatch.setenv('DATA_ENCRYPTION_KEY', Fernet.generate_key().decode())
    from gptmail.config import base_url
    base_url.cache_clear()
    with TestClient(app, base_url='http://localhost:8000') as c:
        yield c
    base_url.cache_clear()


def login(client):
    return client.post('/api/auth/login', json={'password': 'test-password-strong-123'},
                       headers={'Origin': 'http://localhost:8000'})


def admin_action(client, action, data):
    return client.post('/api/admin/action', json={'action': action, 'data': data},
                       headers={'Origin': 'http://localhost:8000'})


def test_folder_codec():
    for folder in ('INBOX', 'Gönderilen Öğeler', 'A&B', '[Gmail]/All Mail', '💌'):
        assert decode_folder(encode_folder(folder)) == folder


def test_login_and_private_routes(client):
    assert client.get('/').status_code == 200
    assert client.get('/api/admin/state').status_code == 401
    assert client.post('/api/auth/login', json={'password': 'nope'},
                       headers={'Origin': 'https://evil.test'}).status_code == 403
    assert login(client).status_code == 200
    state = client.get('/api/admin/state').json()
    assert state['permissions']['read'] is True
    assert state['permissions']['send'] is False
    assert state['permissions']['send_approval'] is True
    assert '/mcp' in state['mcp_url']


def test_permissions_can_be_managed(client):
    assert login(client).status_code == 200
    assert admin_action(client, 'permissions/update', {'send': True, 'delete': True}).status_code == 200
    p = client.get('/api/admin/state').json()['permissions']
    assert p['send'] and p['delete']
    assert p['send_approval'] and p['delete_approval']
    assert admin_action(client, 'permissions/update', {'unknown': True}).status_code == 400


def test_oauth_pkce_flow_and_mcp(client):
    verifier = 'a' * 50
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    redirect_uri = 'https://chatgpt.com/connector_platform_oauth_redirect'
    registration = client.post('/oauth/register', json={'client_name': 'ChatGPT',
        'redirect_uris': [redirect_uri], 'token_endpoint_auth_method': 'none'})
    assert registration.status_code == 201
    cid = registration.json()['client_id']
    auth_args = {'client_id': cid, 'redirect_uri': redirect_uri, 'response_type': 'code',
                 'state': 'state-123', 'code_challenge': challenge, 'code_challenge_method': 'S256',
                 'resource': 'http://localhost:8000/mcp', 'scope': 'mail'}
    assert client.get('/oauth/authorize', params=auth_args).status_code == 200
    consent = client.post('/oauth/authorize', data={**auth_args,
        'password': 'test-password-strong-123', 'approve': 'yes'}, follow_redirects=False)
    assert consent.status_code == 303
    assert consent.headers['location'].startswith(redirect_uri + '?')
    assert 'test-password-strong-123' not in consent.headers['location']
    redirect = parse_qs(urlparse(consent.headers['location']).query)
    assert redirect['state'] == ['state-123']
    assert redirect['iss'] == ['http://localhost:8000']
    token = client.post('/oauth/token', data={
        'grant_type': 'authorization_code', 'code': redirect['code'][0],
        'client_id': cid, 'redirect_uri': redirect_uri, 'code_verifier': verifier,
        'resource': 'http://localhost:8000/mcp'
    })
    assert token.status_code == 200, token.text
    access = token.json()['access_token']
    assert client.post('/mcp', json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
        'protocolVersion': '2025-11-25'}}, headers={'Authorization':'Bearer '+access}).status_code == 200
    list_result = client.post('/mcp', json={'jsonrpc':'2.0','id':2,'method':'tools/list'},
                              headers={'Authorization':'Bearer '+access}).json()['result']['tools']
    names = {t['name'] for t in list_result}
    assert 'list_accounts' in names and 'send_email' not in names
    missing = client.post('/mcp', json={'jsonrpc':'2.0','id':3,'method':'tools/call',
                        'params':{'name':'send_email','arguments':{}}},
                        headers={'Authorization':'Bearer '+access}).json()['result']
    assert missing['isError'] is True
    assert login(client).status_code == 200
    assert admin_action(client, 'connections/revoke', {}).status_code == 200
    assert client.post('/mcp', json={'jsonrpc':'2.0','id':4,'method':'ping'},
                       headers={'Authorization':'Bearer '+access}).status_code == 401


def test_modern_mcp_protocol(client):
    from gptmail.mcp import dispatch_rpc
    discovery = dispatch_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'server/discover'}, modern=True)
    assert discovery['result']['resultType'] == 'complete'
    assert '2026-07-28' in discovery['result']['supportedVersions']
    tools = dispatch_rpc({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}, modern=True)
    assert tools['result']['cacheScope'] == 'private'


def test_smtp_message_validation():
    assert validate_message({'to': ['a@example.com'], 'subject': 'Hey', 'body': 'Hello'})['to'] == ['a@example.com']
    with pytest.raises(MailError):
        validate_message({'to': ['attacker@example.com\nBCC:other@example.com'], 'body': 'x'})


def test_credential_storage_and_account_access(client, monkeypatch):
    import gptmail.store as store
    from gptmail.mcp import call_tool
    assert login(client).status_code == 200
    account = {'name': 'Test mailbox', 'email': 'owner@example.com',
               'imap_host': 'imap.example.com', 'imap_port': 993,
               'username': 'owner@example.com', 'password': 'top-secret-app-password',
               'smtp_host': 'smtp.example.com', 'smtp_port': 465,
               'smtp_username': 'owner@example.com', 'smtp_password': 'top-secret-smtp-password',
               'enabled': True, 'mcp_enabled': True}
    account_id = store.save_account(account)
    assert store.get_account(account_id)['password'] == 'top-secret-app-password'
    assert 'password' not in store.accounts_public()[0]
    assert 'smtp_password' not in store.accounts_public()[0]
    assert account_id in {a['id'] for a in call_tool('list_accounts', {})}
    result = admin_action(client, 'account/access', {'account_id': account_id, 'mcp_enabled': False})
    assert result.status_code == 200
    assert call_tool('list_accounts', {}) == []
    with pytest.raises(MailError):
        call_tool('list_folders', {'account_id': account_id})


def test_outgoing_requires_approval_and_owner_can_approve(client, monkeypatch):
    import gptmail.store as store
    import gptmail.mail as mail
    from gptmail.mcp import call_tool
    assert login(client).status_code == 200
    aid = store.save_account({'name': 'Example', 'email': 'owner@example.com',
        'username': 'owner@example.com', 'password': 'fake', 'imap_host': 'imap.example.com',
        'imap_port': 993, 'smtp_host': 'smtp.example.com', 'smtp_port': 465,
        'smtp_username': 'owner@example.com', 'smtp_password': 'fake', 'mcp_enabled': True})
    assert admin_action(client, 'permissions/update', {'send': True}).status_code == 200
    pending = call_tool('send_email', {'account_id': aid, 'to': ['alice@example.org'],
                         'subject': 'Test', 'body': 'A test body'})
    assert pending['status'] == 'pending_approval'
    queue = client.get('/api/admin/state').json()['pending']
    assert len(queue) == 1 and queue[0]['message']['body'] == 'A test body'
    sent = []
    monkeypatch.setattr(mail, 'send_email', lambda account, message: (sent.append(message), {'sent': True})[1])
    answer = admin_action(client, 'approval/approve', {'id': queue[0]['id']})
    assert answer.status_code == 200, answer.text
    assert len(sent) == 1 and sent[0]['to'] == ['alice@example.org']
    assert client.get('/api/admin/state').json()['pending'] == []


def test_mcp_2026_transport_validates_headers(client):
    from gptmail.auth import issue_tokens
    token = issue_tokens('an-example-client', 'http://localhost:8000/mcp')['access_token']
    req = {'jsonrpc': '2.0', 'id': 12, 'method': 'server/discover',
           'params': {'_meta': {'io.modelcontextprotocol/protocolVersion': '2026-07-28',
                                'io.modelcontextprotocol/clientCapabilities': {}}}}
    headers = {'Authorization': 'Bearer ' + token, 'MCP-Protocol-Version': '2026-07-28',
               'Mcp-Method': 'server/discover'}
    result = client.post('/mcp', json=req, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()['result']['supportedVersions'][0] == '2026-07-28'
    mismatched = client.post('/mcp', json=req, headers={**headers, 'Mcp-Method': 'tools/call'})
    assert mismatched.status_code == 400


@pytest.fixture
def movable_account(client):
    import gptmail.store as store
    account_id = store.save_account({'name': 'Example', 'email': 'owner@example.com',
        'username': 'owner@example.com', 'password': 'fake', 'imap_host': 'imap.example.com',
        'imap_port': 993, 'mcp_enabled': True})
    store.save_permissions({'move': True})
    return account_id


@pytest.mark.parametrize('destination,folders', [
    ('Trash', []),
    ('dElEtEd ItEmS', []),
    ('Deleted Messages', []),
    ('Çöp Kutusu', [{'name': 'Çöp Kutusu', 'flags': [r'\Trash']}]),
    ('[gmail]/trash', [{'name': '[Gmail]/Trash', 'flags': [r'\HasNoChildren', r'\Trash']}]),
])
@pytest.mark.parametrize('delete,approval', [(False, True), (True, True), (True, False)])
def test_move_cannot_bypass_trash_policy(client, monkeypatch, movable_account,
                                        destination, folders, delete, approval):
    import gptmail.store as store
    import gptmail.mail as mail
    from gptmail.mcp import call_tool
    store.save_permissions({'delete': delete, 'delete_approval': approval})
    monkeypatch.setattr(mail, 'list_folders', lambda account: folders)
    moved = []
    monkeypatch.setattr(mail, 'move_email', lambda *args: moved.append(args))

    with pytest.raises(MailError, match='Use delete_message'):
        call_tool('move_message', {'account_id': movable_account, 'uid': '42',
                                  'destination': destination})
    assert moved == []
    assert store.pending_list() == []


def test_move_to_ordinary_folder_still_allowed(client, monkeypatch, movable_account):
    import gptmail.mail as mail
    from gptmail.mcp import call_tool
    monkeypatch.setattr(mail, 'list_folders', lambda account: [
        {'name': 'Trash', 'flags': [r'\Trash']}, {'name': 'Projects', 'flags': []}])
    moved = []
    monkeypatch.setattr(mail, 'move_email', lambda *args: (moved.append(args), {'moved': True})[1])

    result = call_tool('move_message', {'account_id': movable_account, 'uid': '42',
                                      'destination': 'Projects'})
    assert result == {'moved': True}
    assert len(moved) == 1 and moved[0][1:] == ('42', 'Projects', 'INBOX')


def test_move_fails_closed_when_folders_unavailable(client, monkeypatch, movable_account):
    import gptmail.mail as mail
    from gptmail.mcp import call_tool
    def unavailable(account):
        raise MailError('Could not list IMAP folders.')
    monkeypatch.setattr(mail, 'list_folders', unavailable)
    moved = []
    monkeypatch.setattr(mail, 'move_email', lambda *args: moved.append(args))

    with pytest.raises(MailError, match='Could not list'):
        call_tool('move_message', {'account_id': movable_account, 'uid': '42',
                                  'destination': 'Projects'})
    assert moved == []


def test_delete_requires_permission_and_owner_approval(client, monkeypatch, movable_account):
    import gptmail.store as store
    import gptmail.mail as mail
    from gptmail.mcp import call_tool
    deleted = []
    monkeypatch.setattr(mail, 'delete_email', lambda *args: (deleted.append(args), {'moved': True})[1])
    args = {'account_id': movable_account, 'uid': '42'}
    with pytest.raises(MailError, match='disabled'):
        call_tool('delete_message', args)
    store.save_permissions({'delete': True})
    pending = call_tool('delete_message', args)
    assert pending['status'] == 'pending_approval'
    assert deleted == []

    assert login(client).status_code == 200
    answer = admin_action(client, 'approval/approve', {'id': pending['approval_id']})
    assert answer.status_code == 200, answer.text
    assert len(deleted) == 1 and deleted[0][1:] == ('42', 'INBOX')
    assert store.pending_list() == []


class ConsentDocument(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.policies = []
        self.form_actions = []
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'content-security-policy':
            self.policies.append(attrs['content'])
        if tag == 'form':
            self.form_actions.append(attrs.get('action'))


def consent_args(client, redirect_uri, extra_redirects=()):
    registration = client.post('/oauth/register', json={'client_name': 'Test client',
        'redirect_uris': [redirect_uri, *extra_redirects], 'token_endpoint_auth_method': 'none'})
    assert registration.status_code == 201, registration.text
    return {'client_id': registration.json()['client_id'], 'redirect_uri': redirect_uri,
            'response_type': 'code', 'state': 'state-123', 'code_challenge': 'a' * 43,
            'code_challenge_method': 'S256', 'resource': 'http://localhost:8000/mcp', 'scope': 'mail'}


@pytest.mark.parametrize('redirect_uri,origin', [
    ('https://chatgpt.com/connector_platform_oauth_redirect', 'https://chatgpt.com'),
    ('https://client.example:8443/callback', 'https://client.example:8443'),
    ('http://127.0.0.1:4321/callback', 'http://127.0.0.1:4321'),
    ('https://client.example/callback;form-action=*?payload=";script-src=*;x=<img>',
     'https://client.example'),
    ('https://client.example/callback?payload=%22%3B%20form-action%20*', 'https://client.example'),
])
def test_consent_csp_allows_only_selected_callback_origin(client, redirect_uri, origin):
    args = consent_args(client, redirect_uri, ['https://other.example/callback'])
    response = client.get('/oauth/authorize', params=args)
    assert response.status_code == 200, response.text
    document = ConsentDocument(response.text)
    assert document.policies == [
        f"default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; form-action 'self' {origin}; base-uri 'none'"]
    assert document.form_actions == ['/oauth/authorize']


@pytest.mark.parametrize('redirect_uri', [
    'https://client.example;script-src=*/callback',
    'https://*.client.example/callback',
    'https://client.example:*/callback',
    'https://client.example:443;script-src=*/callback',
    'https://client.example:99999/callback',
    'https://client.example\t.evil.example/callback',
    'https://client.example\\@evil.example/callback',
    'https://@client.example/callback',
    'https://client.example/callback\n',
])
def test_registration_rejects_unsafe_callback_origins(client, redirect_uri):
    response = client.post('/oauth/register', json={'redirect_uris': [redirect_uri]})
    assert response.status_code == 400


def test_unregistered_callback_cannot_expand_consent_policy(client):
    args = consent_args(client, 'https://chatgpt.com/connector_platform_oauth_redirect')
    args['redirect_uri'] = 'https://unregistered.example/callback'
    response = client.get('/oauth/authorize', params=args)
    assert response.status_code == 400
    assert not ConsentDocument(response.text).policies
    assert client.post('/oauth/authorize', data={**args,
        'password': 'test-password-strong-123', 'approve': 'yes'}, follow_redirects=False).status_code == 400


def test_production_registration_rejects_http_callback(client, monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    response = client.post('/oauth/register', json={'redirect_uris': ['http://localhost:4321/callback']})
    assert response.status_code == 400
