# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import jwt
from passlib.context import CryptContext

from classroom.config import CLASSROOM_JWT_EXPIRE_DAYS, CLASSROOM_JWT_SECRET

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    return _pwd.verify(plain, hashed)


def create_access_token(
    *,
    user_id: UUID,
    role: str,
    org: str,
    name: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "org": org,
        "name": name,
        "iat": now,
        "exp": now + timedelta(days=CLASSROOM_JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, CLASSROOM_JWT_SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, CLASSROOM_JWT_SECRET, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
