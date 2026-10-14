# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import jwt

from classroom.config import (
    CLASSROOM_FRONTEND_URL,
    CLASSROOM_JWT_SECRET,
    CLASSROOM_SWUFE_CLIENT_ID,
    CLASSROOM_SWUFE_CLIENT_SECRET,
    CLASSROOM_SWUFE_REDIRECT_URI,
    CLASSROOM_SWUFE_SSO_BASE,
    CLASSROOM_SWUFE_SSO_ENABLED,
    CLASSROOM_SWUFE_SSO_MOCK,
    CLASSROOM_SWUFE_TEACHER_IDS,
)

logger = logging.getLogger(__name__)
_ALGORITHM = "HS256"


def swufe_sso_ready() -> bool:
    if not CLASSROOM_SWUFE_SSO_ENABLED:
        return False
    if CLASSROOM_SWUFE_SSO_MOCK:
        return True
    return bool(CLASSROOM_SWUFE_CLIENT_ID and CLASSROOM_SWUFE_CLIENT_SECRET and CLASSROOM_SWUFE_REDIRECT_URI)


def _oauth_urls() -> Dict[str, str]:
    base = CLASSROOM_SWUFE_SSO_BASE.rstrip("/")
    return {
        "authorize": f"{base}/oauth2.0/authorize",
        "token": f"{base}/oauth2.0/accessToken",
        "profile": f"{base}/oauth2.0/profile",
    }


def create_sso_state() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "purpose": "sso_state",
        "nonce": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(payload, CLASSROOM_JWT_SECRET, algorithm=_ALGORITHM)


def verify_sso_state(state: str) -> bool:
    try:
        payload = jwt.decode(state, CLASSROOM_JWT_SECRET, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return False
    return payload.get("purpose") == "sso_state"


def build_authorize_url() -> str:
    urls = _oauth_urls()
    params = {
        "response_type": "code",
        "client_id": CLASSROOM_SWUFE_CLIENT_ID,
        "redirect_uri": CLASSROOM_SWUFE_REDIRECT_URI,
        "state": create_sso_state(),
    }
    return f"{urls['authorize']}?{urllib.parse.urlencode(params)}"


def _http_request(
    url: str,
    *,
    method: str = "GET",
    data: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[int, str]:
    body = None
    req_headers = dict(headers or {})
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=body, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        logger.warning("swufe sso http error %s %s: %s", method, url, raw[:500])
        raise RuntimeError(f"SSO HTTP {exc.code}: {raw[:200]}") from exc


def _parse_token_response(raw: str) -> Dict[str, str]:
    raw = raw.strip()
    if not raw:
        raise RuntimeError("SSO token 响应为空")
    if raw.startswith("{"):
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    out: Dict[str, str] = {}
    for part in raw.split("&"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        out[urllib.parse.unquote_plus(key)] = urllib.parse.unquote_plus(value)
    return out


def exchange_code_for_token(code: str) -> str:
    urls = _oauth_urls()
    status, raw = _http_request(
        urls["token"],
        method="POST",
        data={
            "grant_type": "authorization_code",
            "client_id": CLASSROOM_SWUFE_CLIENT_ID,
            "client_secret": CLASSROOM_SWUFE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": CLASSROOM_SWUFE_REDIRECT_URI,
        },
    )
    if status >= 400:
        raise RuntimeError(f"SSO token 交换失败: HTTP {status}")
    parsed = _parse_token_response(raw)
    token = parsed.get("access_token") or parsed.get("accessToken")
    if not token:
        raise RuntimeError("SSO token 响应缺少 access_token")
    return token


def fetch_profile(access_token: str) -> Dict[str, Any]:
    urls = _oauth_urls()
    url = f"{urls['profile']}?access_token={urllib.parse.quote(access_token)}"
    status, raw = _http_request(url, method="GET")
    if status >= 400:
        raise RuntimeError(f"SSO profile 拉取失败: HTTP {status}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("SSO profile 格式无效")
    return data


def _first_attr(profile: Dict[str, Any], *keys: str) -> Optional[str]:
    attrs = profile.get("attributes")
    if isinstance(attrs, dict):
        for key in keys:
            val = attrs.get(key)
            if isinstance(val, list) and val:
                return str(val[0]).strip() or None
            if isinstance(val, str) and val.strip():
                return val.strip()
    for key in keys:
        val = profile.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, list) and val:
            return str(val[0]).strip() or None
    return None


def parse_swufe_profile(profile: Dict[str, Any]) -> Dict[str, Optional[str]]:
    swufe_id = _first_attr(profile, "id", "uuid", "uid") or str(profile.get("id") or "").strip() or None
    name = _first_attr(profile, "cn", "displayName", "name", "userName") or "财大用户"
    student_id = _first_attr(profile, "studentNumber", "employeeNumber", "uid", "campusId")
    email = _first_attr(profile, "mail", "email")
    if not email and student_id:
        email = f"{student_id.lower()}@swufe.edu.cn"
    elif not email and swufe_id:
        email = f"{swufe_id}@swufe.edu.cn"
    elif not email:
        email = f"swufe_{secrets.token_hex(4)}@swufe.edu.cn"
    affiliation = (_first_attr(profile, "eduPersonAffiliation", "userType", "type") or "").lower()
    return {
        "swufe_id": swufe_id,
        "name": name,
        "student_id": student_id,
        "email": email.strip().lower(),
        "affiliation": affiliation,
    }


def resolve_role(parsed: Dict[str, Optional[str]]) -> str:
    teacher_ids = {x.strip() for x in CLASSROOM_SWUFE_TEACHER_IDS if x.strip()}
    for candidate in (parsed.get("swufe_id"), parsed.get("student_id"), parsed.get("email")):
        if candidate and candidate in teacher_ids:
            return "teacher"
    affiliation = parsed.get("affiliation") or ""
    teacher_hints = ("faculty", "staff", "teacher", "教师", "教职工", "employee")
    if any(h in affiliation for h in teacher_hints):
        return "teacher"
    return "student"


def complete_oauth_login(code: str, state: str) -> Dict[str, Optional[str]]:
    if not verify_sso_state(state):
        raise ValueError("SSO state 无效或已过期")
    access_token = exchange_code_for_token(code)
    profile = fetch_profile(access_token)
    parsed = parse_swufe_profile(profile)
    parsed["role"] = resolve_role(parsed)
    return parsed


def mock_profile(role: str = "student") -> Dict[str, Optional[str]]:
    safe_role = "teacher" if role == "teacher" else "student"
    if safe_role == "teacher":
        return {
            "swufe_id": "mock-teacher-dev",
            "name": "演示教师（SSO Mock）",
            "student_id": "T90001",
            "email": "mock.teacher@swufe.edu.cn",
            "affiliation": "faculty",
            "role": "teacher",
        }
    suffix = secrets.token_hex(3)
    return {
        "swufe_id": f"mock-student-{suffix}",
        "name": "演示学生（SSO Mock）",
        "student_id": f"2025{suffix}",
        "email": f"mock.student.{suffix}@swufe.edu.cn",
        "affiliation": "student",
        "role": "student",
    }


def frontend_callback_url(access_token: str) -> str:
    base = CLASSROOM_FRONTEND_URL.rstrip("/")
    return f"{base}/auth/callback?access_token={urllib.parse.quote(access_token)}"
