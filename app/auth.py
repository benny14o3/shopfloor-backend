import hashlib
import base64
import os
from datetime import datetime, timedelta

SECRET_KEY = "fritsch-shopfloor-secret-2026"

# ─── PASSWORD ─────────────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 260000)
    return "pbkdf2:" + base64.b64encode(salt + dk).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        parts = stored.split(":", 1)
        raw = base64.b64decode(parts[1])
        salt = raw[:16]
        stored_dk = raw[16:]
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 260000)
        return dk == stored_dk
    except Exception:
        return False

# ─── SESSION TOKEN ─────────────────────────

def generate_token(user_id: int, username: str, role: str) -> str:
    """Simple signed token: base64(payload):signature"""
    import hmac
    payload = f"{user_id}:{username}:{role}:{datetime.utcnow().isoformat()}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = base64.b64encode(payload.encode()).decode() + ":" + sig
    return token

def verify_token(token: str) -> dict | None:
    """Returns user info dict or None if invalid"""
    import hmac
    try:
        parts = token.rsplit(":", 1)
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        payload = base64.b64decode(payload_b64).decode()
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        user_id, username, role, ts = payload.split(":", 3)
        # Token valid for 12 hours
        created = datetime.fromisoformat(ts)
        if datetime.utcnow() - created > timedelta(hours=12):
            return None
        return {"user_id": int(user_id), "username": username, "role": role}
    except Exception:
        return None

# ─── PIN (legacy, behalten) ────────────────

def hash_pin(pin: str) -> str:
    return hash_password(pin)

def verify_pin(pin: str, stored: str) -> bool:
    # Legacy bcrypt pins
    try:
        from passlib.hash import bcrypt
        return bcrypt.verify(pin, stored)
    except Exception:
        return verify_password(pin, stored)
