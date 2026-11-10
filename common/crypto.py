"""Encrypts restaurant payment secrets before they are stored (Fernet, key derived from settings)."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    seed = settings.FIELD_ENCRYPTION_KEY or settings.SECRET_KEY
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest()))


def encrypt(value):
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value):
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return ""
