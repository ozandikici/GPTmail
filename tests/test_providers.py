"""Provider OAuth tests use only fake credentials, mail transports and Redis."""
import base64
import hashlib
import io
import json
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from test_gptmail import client, login, admin_action
from gptmail import mail, providers, store


@pytest.fixture
def provider_config(monkeypatch):
    for name in ('GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'MICROSOFT_CLIENT_ID', 'MICROSOFT_CLIENT_SECRET'):
        monkeypatch.setenv(name, 'fake-' + name.lower())
    monkeypatch.setenv('MICROSOFT_TENANT_ID', 'common')


def start(client, provider='google', email='owner@example.com'):
    assert login(client).status_code == 200
    response = client.post(f'/api/admin/providers/{provider}/connect', json={'email': email, 'name': 'Personal'},
                           headers={'Origin': 'http://localhost:8000'})
    assert response.status_code == 200, response.text
    params = parse_qs(urlsplit(response.json()['authorization_url']).query)
    return response, params


def token_response(**overrides):
    return {'access_token': 'fake-access-token', 'refresh_token': 'fake-refresh-token',
            'expires_in': 3600, 'token_type': 'Bearer', **overrides}


def oauth_account(provider='google', **overrides):
    spec = providers.SPECS[provider]
    return {'id': 'example-oauth-account', 'name': 'Example', 'email': 'owner@example.com',
            'username': 'owner@example.com', 'smtp_username': 'owner@example.com',
            'auth_type': 'oauth', 'provider': provider, 'enabled': True, 'mcp_enabled': True,
            'connection_status': 'connected', 'smtp_status': 'connected',
            **{key: spec[key] for key in ('imap_host', 'imap_port', 'smtp_host', 'smtp_port')}, **overrides}


def saved_oauth(provider='google', **token_overrides):
    account = oauth_account(provider)
    tokens = providers._tokens(token_response(), provider)
    tokens.update(token_overrides)
    assert store.save_oauth_account(account, tokens)
    return account, tokens


def test_provider_setup_status_requires_owner_and_hides_credentials(client, monkeypatch):
    for name in ('GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'MICROSOFT_CLIENT_ID', 'MICROSOFT_CLIENT_SECRET'):
        monkeypatch.delenv(name, raising=False)
    assert client.get('/api/admin/providers').status_code == 401
    assert login(client).status_code == 200
    entries = client.get('/api/admin/providers').json()['providers']
    by_id = {item['id']: item for item in entries}
    assert by_id['google']['status'] == by_id['microsoft']['status'] == 'setup_required'
    assert by_id['google']['missing_env'] == ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']
    assert by_id['imap']['status'] == 'ready'
    assert client.get('/api/admin/state').json()['providers'] == entries
    response = client.post('/api/admin/providers/google/connect', json={'email': 'owner@example.com'},
                           headers={'Origin': 'http://localhost:8000'})
    assert response.status_code == 503 and response.json()['detail']['code'] == 'setup_required'


@pytest.mark.parametrize('provider', ['google', 'microsoft'])
def test_provider_connect_state_pkce_cookie_and_encryption(client, provider_config, provider):
    response, params = start(client, provider)
    state = params['state'][0]
    flow_blob = store.redis_cmd.data['gptmail:provider_flow:' + hashlib.sha256(state.encode()).hexdigest()]
    flow = store.decrypt_json(flow_blob)
    expected = base64.urlsafe_b64encode(hashlib.sha256(flow['verifier'].encode()).digest()).rstrip(b'=').decode()
    assert params['code_challenge'] == [expected]
    assert params['code_challenge_method'] == ['S256']
    assert params['redirect_uri'] == [f'http://localhost:8000/oauth/mail/{provider}/callback']
    assert params['login_hint'] == ['owner@example.com']
    assert 'client_secret' not in params and 'code_verifier' not in params
    assert flow['verifier'] not in flow_blob and 'owner@example.com' not in flow_blob
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie and 'Max-Age=600' in cookie
    assert 'Path=/oauth/mail/' in cookie


def test_connect_blocks_cross_origin_and_invalid_tenant(client, provider_config, monkeypatch):
    assert login(client).status_code == 200
    response = client.post('/api/admin/providers/google/connect', json={'email': 'owner@example.com'},
                           headers={'Origin': 'https://evil.example'})
    assert response.status_code == 403
    monkeypatch.setenv('MICROSOFT_TENANT_ID', '../attacker')
    status = next(item for item in providers.provider_status() if item['id'] == 'microsoft')
    assert status['status'] == 'setup_required'
    assert status['missing_env'] == ['MICROSOFT_TENANT_ID']


@pytest.mark.parametrize('provider', ['google', 'microsoft'])
def test_callback_binds_flow_without_strict_session_cookie_and_stores_tokens_privately(
        client, provider_config, monkeypatch, provider):
    _, params = start(client, provider)
    exchanges = []
    monkeypatch.setattr(providers, '_token_request', lambda spec, fields:
                        (exchanges.append(fields), token_response())[1])
    verified = []
    monkeypatch.setattr(mail, 'test_imap', lambda account: (verified.append(account.copy()), True)[1])
    monkeypatch.setattr(mail, 'test_smtp', lambda account: True)
    client.cookies.delete('gptmail_session')  # Cross-site browser callback omits Strict cookie.
    response = client.get(f'/oauth/mail/{provider}/callback',
                          params={'state': params['state'][0], 'code': 'fake-code'}, follow_redirects=False)
    assert response.status_code == 303
    assert parse_qs(urlsplit(response.headers['location']).query) == {'provider_connected': [provider]}
    assert exchanges[0]['code_verifier'] and exchanges[0]['code'] == 'fake-code'
    assert verified[0]['_oauth_access_token'] == 'fake-access-token'
    public = store.accounts_public()[0]
    assert public['auth_type'] == 'oauth' and public['smtp_status'] == 'connected'
    assert '_oauth_access_token' not in store.get_account(public['id'])
    _, tokens = store.oauth_token_record(public['id'])
    assert tokens['refresh_token'] == 'fake-refresh-token'
    assert 'fake-access-token' not in str(store.redis_cmd.data)
    assert 'fake-refresh-token' not in str(store.redis_cmd.data)
    assert login(client).status_code == 200
    assert 'fake-access-token' not in client.get('/api/admin/state').text
    assert 'fake-refresh-token' not in client.get('/api/admin/state').text
    replay = client.get(f'/oauth/mail/{provider}/callback',
                        params={'state': params['state'][0], 'code': 'fake-code'}, follow_redirects=False)
    assert 'provider_error=state_invalid' in replay.headers['location']
    assert len(exchanges) == 1


@pytest.mark.parametrize('failure', ['no_cookie', 'wrong_cookie', 'wrong_provider', 'logged_out', 'cancelled'])
def test_callback_rejects_invalid_bindings_before_token_exchange(client, provider_config, monkeypatch, failure):
    _, params = start(client)
    exchanges = []
    monkeypatch.setattr(providers, '_token_request', lambda *args: exchanges.append(args))
    provider = 'google'
    query = {'state': params['state'][0], 'code': 'fake-code'}
    if failure == 'no_cookie':
        client.cookies.delete(providers.FLOW_COOKIE)
    elif failure == 'wrong_cookie':
        client.cookies.delete(providers.FLOW_COOKIE)
        client.cookies.set(providers.FLOW_COOKIE, 'wrong-browser-secret', path='/oauth/mail/')
    elif failure == 'wrong_provider':
        provider = 'microsoft'
    elif failure == 'logged_out':
        client.post('/api/auth/logout', headers={'Origin': 'http://localhost:8000'})
    elif failure == 'cancelled':
        query.update(error='access_denied', error_description='untrusted-sensitive-text')
    response = client.get(f'/oauth/mail/{provider}/callback', params=query, follow_redirects=False)
    assert 'provider_error=' in response.headers['location']
    assert 'untrusted-sensitive-text' not in response.headers['location']
    assert exchanges == [] and store.accounts_public() == []


def test_callback_requires_mailbox_imap_verification(client, provider_config, monkeypatch):
    _, params = start(client)
    monkeypatch.setattr(providers, '_token_request', lambda *args: token_response())
    def failed(account):
        raise mail.MailError('mailbox failure with sensitive upstream text')
    monkeypatch.setattr(mail, 'test_imap', failed)
    response = client.get('/oauth/mail/google/callback', params={'state': params['state'][0], 'code': 'fake'},
                          follow_redirects=False)
    assert 'provider_error=mailbox_auth_failed' in response.headers['location']
    assert store.accounts_public() == []
    assert not any(key.startswith('gptmail:provider_tokens:') for key in store.redis_cmd.data)


def test_callback_can_connect_imap_when_microsoft_smtp_disabled(client, provider_config, monkeypatch):
    _, params = start(client, 'microsoft')
    monkeypatch.setattr(providers, '_token_request', lambda *args: token_response())
    monkeypatch.setattr(mail, 'test_imap', lambda account: True)
    def smtp_disabled(account):
        raise mail.MailError('SMTP AUTH disabled')
    monkeypatch.setattr(mail, 'test_smtp', smtp_disabled)
    response = client.get('/oauth/mail/microsoft/callback', params={'state': params['state'][0], 'code': 'fake'},
                          follow_redirects=False)
    assert 'provider_connected=microsoft' in response.headers['location']
    assert store.accounts_public()[0]['smtp_status'] == 'unavailable'


def test_microsoft_personal_smtp_uses_only_verified_fixed_alternate(client, provider_config, monkeypatch):
    _, params = start(client, 'microsoft')
    monkeypatch.setattr(providers, '_token_request', lambda *args: token_response())
    monkeypatch.setattr(mail, 'test_imap', lambda account: True)
    tested = []
    def personal_smtp(account):
        tested.append(account['smtp_host'])
        assert providers.oauth_access_token(account) == 'fake-access-token'
        return account['smtp_host'] == 'smtp-mail.outlook.com'
    monkeypatch.setattr(mail, 'test_smtp', personal_smtp)
    response = client.get('/oauth/mail/microsoft/callback', params={'state': params['state'][0], 'code': 'fake'},
                          follow_redirects=False)
    assert 'provider_connected=microsoft' in response.headers['location']
    assert tested == ['smtp.office365.com', 'smtp-mail.outlook.com']
    account = store.accounts_public()[0]
    assert account['smtp_host'] == 'smtp-mail.outlook.com' and account['smtp_status'] == 'connected'
    with pytest.raises(providers.ProviderError, match='endpoints'):
        providers.oauth_access_token({**account, 'smtp_host': 'attacker.example'})


def test_callback_does_not_store_access_only_grant(client, provider_config, monkeypatch):
    _, params = start(client)
    response_tokens = token_response()
    del response_tokens['refresh_token']
    monkeypatch.setattr(providers, '_token_request', lambda *args: response_tokens)
    response = client.get('/oauth/mail/google/callback', params={'state': params['state'][0], 'code': 'fake'},
                          follow_redirects=False)
    assert 'provider_error=reconnect_required' in response.headers['location']
    assert store.accounts_public() == []


def test_transient_refresh_failure_does_not_mark_consent_revoked(client, provider_config, monkeypatch):
    account, _ = saved_oauth(expires_at=time.time() - 30)
    def unavailable(*args):
        raise providers.ProviderError('provider_unavailable', 'Try again later.')
    monkeypatch.setattr(providers, '_token_request', unavailable)
    with pytest.raises(providers.ProviderError, match='Try again'):
        providers.oauth_access_token(account)
    assert store.accounts_public()[0]['connection_status'] == 'connected'


@pytest.mark.parametrize('provider', ['google', 'microsoft'])
def test_oauth_refresh_preserves_or_rotates_refresh_token(client, provider_config, monkeypatch, provider):
    account, old = saved_oauth(provider, expires_at=time.time() - 30)
    requests = []
    result = token_response(access_token='renewed-access')
    if provider == 'google':
        del result['refresh_token']
    else:
        result['refresh_token'] = 'rotated-refresh'
    monkeypatch.setattr(providers, '_token_request', lambda spec, fields: (requests.append(fields), result)[1])
    assert providers.oauth_access_token(account) == 'renewed-access'
    _, current = store.oauth_token_record(account['id'])
    assert current['refresh_token'] == ('fake-refresh-token' if provider == 'google' else 'rotated-refresh')
    assert requests[0]['grant_type'] == 'refresh_token'
    assert requests[0]['refresh_token'] == old['refresh_token']
    assert providers.oauth_access_token(account) == 'renewed-access'
    assert len(requests) == 1  # Cached unexpired token avoids another provider request.


def test_refresh_cannot_resurrect_deleted_account(client, provider_config, monkeypatch):
    account, _ = saved_oauth(expires_at=time.time() - 30)
    def removed_during_refresh(*args):
        store.remove_account(account['id'])
        return token_response(access_token='renewed-access')
    monkeypatch.setattr(providers, '_token_request', removed_during_refresh)
    with pytest.raises(providers.ProviderError, match='removed or changed'):
        providers.oauth_access_token(account)
    assert store.get_account(account['id']) is None
    assert store.oauth_token_record(account['id']) == (None, None)


def test_refresh_cannot_overwrite_newer_tokens(client, provider_config, monkeypatch):
    account, _ = saved_oauth(expires_at=time.time() - 30)
    def simultaneous_refresh(*args):
        blob, _ = store.oauth_token_record(account['id'])
        tokens = providers._tokens(token_response(access_token='other-worker-token'), 'google')
        assert store.replace_oauth_tokens(account['id'], blob, tokens)
        return token_response(access_token='late-worker-token')
    monkeypatch.setattr(providers, '_token_request', simultaneous_refresh)
    assert providers.oauth_access_token(account) == 'other-worker-token'
    assert store.oauth_token_record(account['id'])[1]['access_token'] == 'other-worker-token'


def test_revoked_refresh_marks_reconnect_without_leaking_response(client, provider_config, monkeypatch):
    account, _ = saved_oauth(expires_at=time.time() - 30)
    def revoked(*args):
        raise providers.ProviderError('reconnect_required', 'Reconnect this account.')
    monkeypatch.setattr(providers, '_token_request', revoked)
    with pytest.raises(providers.ProviderError, match='Reconnect'):
        providers.oauth_access_token(account)
    assert store.accounts_public()[0]['connection_status'] == 'reconnect_required'


def test_token_endpoint_error_does_not_expose_provider_body(monkeypatch, provider_config):
    class FailedOpener:
        def open(self, *args, **kwargs):
            raise HTTPError('https://oauth2.googleapis.com/token', 400, 'Bad Request', {},
                            io.BytesIO(b'{"error":"invalid_grant","error_description":"fake-sensitive-provider-body"}'))
    monkeypatch.setattr(providers, 'build_opener', lambda *args: FailedOpener())
    with pytest.raises(providers.ProviderError) as caught:
        providers._token_request(providers._config('google'), {'grant_type': 'refresh_token'})
    assert caught.value.code == 'reconnect_required'
    assert 'fake-sensitive-provider-body' not in str(caught.value)


def test_oauth_account_rejects_endpoint_edits_and_cleans_tokens_on_remove(client):
    account, _ = saved_oauth()
    assert login(client).status_code == 200
    assert admin_action(client, 'account/update', {'account_id': account['id'],
                        'imap_host': 'attacker.example'}).status_code == 400
    assert admin_action(client, 'account/update', {'account_id': account['id'],
                        'name': 'Renamed mailbox'}).status_code == 200
    assert store.get_account(account['id'])['name'] == 'Renamed mailbox'
    changed = {**account, 'imap_host': 'attacker.example'}
    with pytest.raises(providers.ProviderError, match='endpoints'):
        providers.oauth_access_token(changed)
    assert admin_action(client, 'account/remove', {'account_id': account['id']}).status_code == 200
    assert store.oauth_token_record(account['id']) == (None, None)


def test_imap_xoauth2_uses_bearer_and_empty_error_challenge(client, monkeypatch):
    account, _ = saved_oauth()
    class FakeIMAP:
        def __init__(self, *args, **kwargs): pass
        def authenticate(self, mechanism, respond):
            assert mechanism == 'XOAUTH2'
            assert respond(b'') == b'user=owner@example.com\x01auth=Bearer fake-access-token\x01\x01'
            assert respond(b'error-challenge') == b''
            return 'OK', []
        def logout(self): pass
    monkeypatch.setattr(mail.imaplib, 'IMAP4_SSL', FakeIMAP)
    with mail.imap_connection(account):
        pass


def test_smtp_xoauth2_uses_tls_bearer_without_password_login(client, monkeypatch):
    account, _ = saved_oauth('microsoft')
    calls = []
    class FakeSMTP:
        def __init__(self, *args, **kwargs): pass
        def ehlo(self): calls.append('ehlo')
        def has_extn(self, name): return name == 'starttls'
        def starttls(self, **kwargs): calls.append('tls')
        def docmd(self, command, value=''):
            assert 'tls' in calls and command == 'AUTH'
            assert value.startswith('XOAUTH2 ')
            decoded = base64.b64decode(value.split(' ', 1)[1]).decode()
            assert decoded == 'user=owner@example.com\x01auth=Bearer fake-access-token\x01\x01'
            calls.append('auth')
            return 235, b'Authenticated'
        def quit(self): pass
    monkeypatch.setattr(mail.smtplib, 'SMTP', FakeSMTP)
    with mail.smtp_connection(account):
        pass
    assert calls.index('tls') < calls.index('auth')


def test_generic_password_mailbox_still_authenticates(monkeypatch):
    account = mail.validated_account({'name': 'Generic', 'email': 'owner@example.com',
        'username': 'owner@example.com', 'password': 'fake-password',
        'imap_host': 'imap.example.com', 'smtp_host': 'smtp.example.com'})
    logins = []
    class FakeIMAP:
        def __init__(self, *args, **kwargs): pass
        def login(self, username, password):
            logins.append((username, password))
            return 'OK', []
        def logout(self): pass
    monkeypatch.setattr(mail.imaplib, 'IMAP4_SSL', FakeIMAP)
    with mail.imap_connection(account):
        pass
    assert account['auth_type'] == 'password' and account['provider'] == 'imap'
    assert logins == [('owner@example.com', 'fake-password')]
