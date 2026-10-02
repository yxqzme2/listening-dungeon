# -----------------------------------------
# game_auth.py — Player sessions for The Listening Dungeon
# -----------------------------------------
# Players log in with their ABS username and a 4-digit PIN (stored hashed in
# user_pins by StateStore). A successful login sets a signed cookie that
# lasts 30 days. The signing secret is kept next to the database so a
# container restart doesn't log everyone out.
# -----------------------------------------

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from typing import Optional

COOKIE_NAME = "ld_session"
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
PIN_RE = re.compile(r"^\d{4}$")

MAX_PIN_FAILURES = 5
LOCKOUT_SECONDS = 5 * 60

_lock = threading.Lock()
_failures = {}  # user_id -> {"fails": int, "locked_until": float}
_secret: Optional[bytes] = None


def init(secret_dir: str) -> None:
    """Load the session secret from `secret_dir`, creating it on first run."""
    global _secret
    path = os.path.join(secret_dir, ".game_session_secret")
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = f.read().strip()
    except FileNotFoundError:
        value = ""
    if len(value) < 32:
        value = secrets.token_hex(32)
        os.makedirs(secret_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    _secret = value.encode("utf-8")


def _sig(user_id: str, expiry: int) -> str:
    if _secret is None:
        raise RuntimeError("game_auth.init() has not been called")
    return hmac.new(_secret, f"player:{user_id}:{expiry}".encode("utf-8"), hashlib.sha256).hexdigest()


def make_token(user_id: str, now: Optional[int] = None) -> str:
    expiry = int(now if now is not None else time.time()) + SESSION_TTL_SECONDS
    return f"{user_id}.{expiry}.{_sig(user_id, expiry)}"


def user_from_token(token: str, now: Optional[int] = None) -> Optional[str]:
    """Return the user id a valid token belongs to, or None."""
    parts = (token or "").split(".")
    if len(parts) != 3:
        return None
    user_id, expiry_s, sig = parts
    try:
        expiry = int(expiry_s)
    except ValueError:
        return None
    if not user_id or expiry < int(now if now is not None else time.time()):
        return None
    return user_id if hmac.compare_digest(_sig(user_id, expiry), sig) else None


def valid_pin(pin: str) -> bool:
    return bool(PIN_RE.match(pin or ""))


# ── wrong-PIN lockout, per player ────────────────────────────────────────
def lockout_remaining(user_id: str) -> int:
    with _lock:
        rec = _failures.get(user_id)
        if not rec:
            return 0
        left = rec["locked_until"] - time.time()
        return int(left) + 1 if left > 0 else 0


def record_failure(user_id: str) -> None:
    with _lock:
        rec = _failures.setdefault(user_id, {"fails": 0, "locked_until": 0.0})
        rec["fails"] += 1
        if rec["fails"] >= MAX_PIN_FAILURES:
            rec["fails"] = 0
            rec["locked_until"] = time.time() + LOCKOUT_SECONDS


def record_success(user_id: str) -> None:
    with _lock:
        _failures.pop(user_id, None)
