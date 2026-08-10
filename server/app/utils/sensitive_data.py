import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import ConflictError


def _cipher() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode('utf-8')).digest())
    return Fernet(key)


def encrypt_sensitive(value: str) -> str:
    return _cipher().encrypt(value.encode('utf-8')).decode('ascii')


def decrypt_sensitive(value: str) -> str:
    try:
        return _cipher().decrypt(value.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError) as exc:
        raise ConflictError('Sensitive data cannot be decrypted with the current secret key') from exc


def mask_bank_card(last_four: str) -> str:
    return f'**** **** **** {last_four}'

