#!/usr/bin/env python3
"""Generate deploy-time secrets; prints private values to your local terminal only."""
import getpass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cryptography.fernet import Fernet
from gptmail.auth import make_hash

if __name__ == '__main__':
    password = getpass.getpass('New GPTmail owner password (at least 12 characters): ')
    repeat = getpass.getpass('Confirm password: ')
    if password != repeat:
        raise SystemExit('Passwords do not match.')
    print('\nStore these in Vercel > Settings > Environment Variables; NEVER commit them:\n')
    print('ADMIN_PASSWORD_HASH=' + make_hash(password))
    print('DATA_ENCRYPTION_KEY=' + Fernet.generate_key().decode())
