import bcrypt

# As a solution to this error `AttributeError: module 'bcrypt' has no attribute '__about__'`. I did the below
bcrypt.__about__ = bcrypt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Any
import jwt

from app.core.config import settings

code_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_code(plain_code: str, hashed_code: str) -> bool:
    return code_context.verify(plain_code, hashed_code)


def get_code_hash(code: str) -> str:
    return code_context.hash(code)
