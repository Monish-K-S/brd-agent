from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


@lru_cache
def get_fernet() -> Fernet:
    return Fernet(settings.token_encryption_key)


def encrypt_token(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    return get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def decrypt_token_or_legacy(value: str) -> tuple[str, bool]:
    try:
        return decrypt_token(value), True
    except InvalidToken:
        return value, False
