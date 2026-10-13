# Hashing config

import hashlib, json

# Sha
def sha(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha1(raw).hexdigest()[:10]

# Chain
def chain(*parts: str) -> str:
    return sha(list(parts))