# ============================================================
# crypto.py — Anchor Cloud Encryption Engine
#
# ISOLATED MODULE — zero business logic here.
# All cryptographic operations are contained in this file.
#
# Algorithm : AES-256 in EAX mode
#   - Provides authenticated encryption (confidentiality + integrity)
#   - Nonce is randomly generated per file (16 bytes)
#   - MAC tag is 16 bytes
#   - Key is 32 bytes (256 bits) derived via PBKDF2-HMAC-SHA256
#
# On-disk blob format:
#   [ 16 bytes nonce ][ 16 bytes tag ][ N bytes ciphertext ]
#
# Key derivation:
#   PBKDF2(password=user_id, salt=MASTER_SALT, iterations=200_000, dklen=32)
#   The user_id acts as a per-user secret; MASTER_SALT is the server secret.
#   This means even if the database leaks, blobs cannot be decrypted without
#   the MASTER_SALT from the server environment.
# ============================================================

import os
import hashlib
import hmac

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from config import settings


# ── Constants ────────────────────────────────────────────────
NONCE_SIZE   = 16   # bytes
TAG_SIZE     = 16   # bytes
KEY_SIZE     = 32   # bytes — AES-256
PBKDF2_ITERS = 200_000


# ── Key Derivation ───────────────────────────────────────────

def derive_key(user_id: str) -> bytes:
    """
    Derives a deterministic 256-bit AES key for a given user.

    Uses PBKDF2-HMAC-SHA256 with:
      - password  : user_id (UTF-8 encoded)
      - salt      : MASTER_SALT from server environment
      - iterations: 200,000
      - dklen     : 32 bytes

    The key is NOT stored anywhere — it is re-derived on every
    encrypt/decrypt call. MASTER_SALT must be kept secret.
    """
    salt = settings.MASTER_SALT.encode("utf-8")

    key = hashlib.pbkdf2_hmac(
        hash_name   = "sha256",
        password    = user_id.encode("utf-8"),
        salt        = salt,
        iterations  = PBKDF2_ITERS,
        dklen       = KEY_SIZE,
    )
    return key


# ── Encryption ───────────────────────────────────────────────

def encrypt_file(plaintext: bytes, user_id: str) -> bytes:
    """
    Encrypts raw file bytes using AES-256-EAX.

    Args:
        plaintext : Raw file bytes to encrypt.
        user_id   : Owner's user ID — used to derive the AES key.

    Returns:
        Encrypted blob:
          [ 16-byte nonce ][ 16-byte tag ][ ciphertext ]

    Raises:
        ValueError : if plaintext is empty.
    """
    if not plaintext:
        raise ValueError("Cannot encrypt empty plaintext.")

    key   = derive_key(user_id)
    nonce = get_random_bytes(NONCE_SIZE)

    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce, mac_len=TAG_SIZE)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)

    # Prepend nonce + tag to the ciphertext for self-contained blob
    return nonce + tag + ciphertext


def decrypt_file(blob: bytes, user_id: str) -> bytes:
    """
    Decrypts a blob produced by `encrypt_file`.

    Args:
        blob    : The encrypted blob (nonce + tag + ciphertext).
        user_id : Owner's user ID — used to re-derive the AES key.

    Returns:
        Original plaintext bytes.

    Raises:
        ValueError          : if blob is too short.
        CryptoError (ValueError from PyCryptodome) : if MAC verification fails
                              — indicates tampering or wrong key.
    """
    min_size = NONCE_SIZE + TAG_SIZE + 1
    if len(blob) < min_size:
        raise ValueError(f"Blob too short: {len(blob)} bytes (minimum {min_size}).")

    nonce      = blob[:NONCE_SIZE]
    tag        = blob[NONCE_SIZE : NONCE_SIZE + TAG_SIZE]
    ciphertext = blob[NONCE_SIZE + TAG_SIZE :]

    key    = derive_key(user_id)
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce, mac_len=TAG_SIZE)

    # verify() raises ValueError if MAC does not match
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext


# ── Integrity Check ──────────────────────────────────────────

def verify_blob_integrity(blob: bytes, user_id: str) -> bool:
    """
    Returns True if the blob decrypts without MAC failure.
    Does NOT return the plaintext — use decrypt_file for that.
    """
    try:
        decrypt_file(blob, user_id)
        return True
    except (ValueError, KeyError):
        return False


# ── Blob Helpers ─────────────────────────────────────────────

def extract_nonce(blob: bytes) -> bytes:
    """Returns the nonce portion of an encrypted blob."""
    return blob[:NONCE_SIZE]


def get_blob_metadata(blob: bytes) -> dict:
    """
    Returns metadata about an encrypted blob without decrypting it.
    Useful for logging and debugging.
    """
    return {
        "total_size"       : len(blob),
        "nonce_hex"        : extract_nonce(blob).hex(),
        "ciphertext_size"  : len(blob) - NONCE_SIZE - TAG_SIZE,
        "algorithm"        : "AES-256-EAX",
        "key_derivation"   : f"PBKDF2-HMAC-SHA256 ({PBKDF2_ITERS} iterations)",
    }


# ── Password Hashing (for auth module) ───────────────────────
# Exposed here to keep all crypto in one module.
# The auth module imports these instead of using passlib directly.

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Returns a bcrypt hash of the given password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    return _pwd_context.verify(plain, hashed)