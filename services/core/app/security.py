import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta

import jwt

from app.config import settings
from app.db import utcnow
from app.models import User

PBKDF2_ITERATIONS = 200_000
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(actual, digest)


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "exp": utcnow() + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(confirmation_id: uuid.UUID, code: str) -> str:
    message = f"{confirmation_id}:{code}".encode()
    return hmac.new(settings.jwt_secret.encode(), message, hashlib.sha256).hexdigest()
