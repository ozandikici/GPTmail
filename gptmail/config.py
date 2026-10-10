"""Security-sensitive configuration; intentionally never log secrets."""
from __future__ import annotations

import os
from functools import lru_cache


class ConfigurationError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def base_url() -> str:
    raw = os.getenv('APP_BASE_URL', '').strip().rstrip('/')
    if not raw and os.getenv('VERCEL_PROJECT_PRODUCTION_URL'):
        raw = 'https://' + os.environ['VERCEL_PROJECT_PRODUCTION_URL'].strip().rstrip('/')
    if not raw and not os.getenv('VERCEL'):
        raw = 'http://localhost:8000'
    if not raw or not (raw.startswith('https://') or raw.startswith('http://localhost:')):
        raise ConfigurationError('Set APP_BASE_URL to the public HTTPS URL of your production deployment.')
    return raw


def resource_url() -> str:
    return base_url() + '/mcp'


def must_env(name: str) -> str:
    value = os.getenv(name, '').strip()
    if not value:
        raise ConfigurationError(f'Missing required environment variable: {name}')
    return value


def is_production() -> bool:
    return bool(os.getenv('VERCEL')) or base_url().startswith('https://')


DEFAULT_PERMISSIONS = {
    'read': True,
    'attachments': False,
    'send': False,
    'reply': False,
    'forward': False,
    'save_draft': False,
    'mark': False,
    'move': False,
    'delete': False,
    'create_folder': False,
    'send_approval': True,
    'delete_approval': True,
}

PERMISSION_LABELS = {
    'read': 'Read mail, folders and search',
    'attachments': 'Download attachments',
    'send': 'Send new email',
    'reply': 'Reply to email',
    'forward': 'Forward email',
    'save_draft': 'Save IMAP drafts',
    'mark': 'Mark read / unread / starred',
    'move': 'Move or archive email',
    'delete': 'Move email to Trash',
    'create_folder': 'Create mailbox folders',
    'send_approval': 'Require dashboard approval for outgoing mail',
    'delete_approval': 'Require dashboard approval before moving to Trash',
}
