# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        root = Path(__file__).resolve().parent.parent
        for path in (root / ".env", Path.cwd() / ".env"):
            if path.exists():
                load_dotenv(path, override=True)
                break
    except ImportError:
        pass


_load_dotenv()

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
CLASSROOM_JWT_SECRET = (os.getenv("CLASSROOM_JWT_SECRET") or "classroom-dev-secret-change-me").strip()
CLASSROOM_JWT_EXPIRE_DAYS = max(1, int(os.getenv("CLASSROOM_JWT_EXPIRE_DAYS") or "7"))
CLASSROOM_AUTO_CREATE_TABLES = (os.getenv("CLASSROOM_AUTO_CREATE_TABLES") or "1").strip().lower() in (
    "1",
    "true",
    "yes",
)
CLASSROOM_SEED_DEMO = (os.getenv("CLASSROOM_SEED_DEMO") or "0").strip().lower() in ("1", "true", "yes")
_register_env = os.getenv("CLASSROOM_ALLOW_REGISTER")
if _register_env is not None:
    CLASSROOM_ALLOW_REGISTER = _register_env.strip().lower() in ("1", "true", "yes")
else:
    # 演示/本地开发默认开放注册；生产环境请显式设 CLASSROOM_ALLOW_REGISTER=0
    CLASSROOM_ALLOW_REGISTER = CLASSROOM_SEED_DEMO
CLASSROOM_ALLOW_LOCAL_LOGIN = (os.getenv("CLASSROOM_ALLOW_LOCAL_LOGIN") or "1").strip().lower() in (
    "1",
    "true",
    "yes",
)
CLASSROOM_FRONTEND_URL = (os.getenv("CLASSROOM_FRONTEND_URL") or "http://localhost:3000").strip().rstrip("/")
CLASSROOM_SWUFE_SSO_ENABLED = (os.getenv("CLASSROOM_SWUFE_SSO_ENABLED") or "0").strip().lower() in (
    "1",
    "true",
    "yes",
)
CLASSROOM_SWUFE_SSO_MOCK = (os.getenv("CLASSROOM_SWUFE_SSO_MOCK") or "0").strip().lower() in (
    "1",
    "true",
    "yes",
)
CLASSROOM_SWUFE_CLIENT_ID = (os.getenv("CLASSROOM_SWUFE_CLIENT_ID") or os.getenv("SWUFE_SSO_CLIENT_ID") or "").strip()
CLASSROOM_SWUFE_CLIENT_SECRET = (
    os.getenv("CLASSROOM_SWUFE_CLIENT_SECRET") or os.getenv("SWUFE_SSO_CLIENT_SECRET") or ""
).strip()
CLASSROOM_SWUFE_REDIRECT_URI = (
    os.getenv("CLASSROOM_SWUFE_REDIRECT_URI") or os.getenv("SWUFE_SSO_REDIRECT_URI") or ""
).strip()
CLASSROOM_SWUFE_SSO_BASE = (
    os.getenv("CLASSROOM_SWUFE_SSO_BASE") or "https://authserver.swufe.edu.cn/authserver"
).strip().rstrip("/")
CLASSROOM_SWUFE_TEACHER_IDS = [
    x.strip()
    for x in (os.getenv("CLASSROOM_SWUFE_TEACHER_IDS") or os.getenv("CLASSROOM_SWUFE_TEACHER_UIDS") or "").split(",")
    if x.strip()
]
CLASSROOM_DEFAULT_CLASS_ID = int(os.getenv("CLASSROOM_DEFAULT_CLASS_ID") or "0")


def classroom_enabled() -> bool:
    if not DATABASE_URL:
        return False
    try:
        import sqlalchemy as sa

        return str(getattr(sa, "__version__", "0") or "0").startswith("2.")
    except ImportError:
        return False
