"""Authenticated, password-protected portable portfolio backups."""
from os import urandom
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from hashlib import scrypt

MAGIC = b'HomeInvestBackup\x01'
LIMIT = 25 * 1024 * 1024
OVERHEAD = len(MAGIC) + 16 + 12 + 16


def _cipher(password, salt):
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError('Gebruik een back-upwachtwoord van 12 tot 128 tekens.')
    key = scrypt(password.encode(), salt=salt, n=2**16, r=8, p=1,
                 maxmem=96 * 1024 * 1024, dklen=32)
    return AESGCM(key)


def encrypt(content, password):
    if len(content) > LIMIT:
        raise ValueError('Deze back-up is groter dan 25 MB.')
    salt, nonce = urandom(16), urandom(12)
    header = MAGIC + salt + nonce
    return header + _cipher(password, salt).encrypt(nonce, content, header)


def decrypt(content, password):
    if not content.startswith(MAGIC):
        return content
    if not OVERHEAD <= len(content) <= LIMIT + OVERHEAD:
        raise ValueError('Ongeldige versleutelde back-up.')
    offset = len(MAGIC)
    salt, nonce = content[offset:offset+16], content[offset+16:offset+28]
    header = content[:offset+28]
    try:
        return _cipher(password, salt).decrypt(nonce, content[len(header):], header)
    except InvalidTag:
        raise ValueError('Het back-upwachtwoord is onjuist of het bestand is beschadigd.') from None
