from hashlib import md5
import os

HASH_SALT = None

with open(os.environ.get("PUBLIC_KEY_FILE"), 'rb') as f:
    HASH_SALT = f.read()

HASH_DEFAULT_LENGTH = 7

def generate_hash(s: str, length: int = HASH_DEFAULT_LENGTH) -> str:
    if HASH_SALT is None:
        raise ValueError("HASH_SALT is not ready")

    s_bytes = s.encode()
    s_bytes += HASH_SALT
    return md5(s_bytes).hexdigest()[:length]
