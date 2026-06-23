"""Password hashing and session-token generation.

Passwords are hashed with PBKDF2-HMAC-SHA256 using a per-password random salt.
This keeps the dependency footprint tiny (stdlib only) while still storing
credentials in a properly salted, slow-to-brute-force form. The stored format is:

    pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
"""

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 120_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations_s, salt_hex, hash_hex = stored.split("$")
        if algorithm != _ALGORITHM:
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    except (ValueError, AttributeError):
        return False
    # Constant-time comparison to avoid leaking timing information.
    return hmac.compare_digest(digest.hex(), hash_hex)


def generate_token() -> str:
    """Return a cryptographically random, URL-safe session token."""
    return secrets.token_urlsafe(32)
