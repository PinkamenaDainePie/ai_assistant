# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuthConfigResponse(BaseModel):
    enabled: bool
    allow_register: bool
    swufe_sso_enabled: bool = False
    allow_local_login: bool = True


class UserPublic(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    org: str
    student_id: Optional[str] = None


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=4, max_length=128)


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=4, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    role: str = Field(default="student", pattern="^(student|teacher)$")
    student_id: Optional[str] = Field(default=None, max_length=64)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ClassInfo(BaseModel):
    id: int
    name: str
    course_name: str
    semester: str


class PlaythroughCreate(BaseModel):
    scenario_code: str = Field(..., min_length=1, max_length=64)
    game_session_id: str = Field(..., min_length=1, max_length=128)
    campaign_session_id: Optional[str] = Field(default=None, max_length=128)


class PlaythroughUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(in_progress|finished|abandoned)$")
    current_quarter: Optional[int] = Field(default=None, ge=0, le=99)
    ending_type: Optional[str] = Field(default=None, max_length=128)
    summary_json: Optional[Dict[str, Any]] = None
    campaign_session_id: Optional[str] = Field(default=None, max_length=128)
    quarter_chapters: Optional[List[Dict[str, Any]]] = None


class PlaythroughPublic(BaseModel):
    id: UUID
    user_id: UUID
    scenario_code: str
    game_session_id: str
    status: str
    current_quarter: int
    ending_type: Optional[str] = None
    summary_json: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    finished_at: Optional[datetime] = None
    student_name: Optional[str] = None
    student_id: Optional[str] = None
    teacher_review_score: Optional[int] = None
    teacher_review_comment: Optional[str] = None
    teacher_review_at: Optional[datetime] = None
    quarter_chapters: List[Dict[str, Any]] = Field(default_factory=list)


class PlaythroughReviewRequest(BaseModel):
    score: int = Field(..., ge=0, le=100)
    comment: Optional[str] = Field(default=None, max_length=2000)


class PlaythroughListResponse(BaseModel):
    items: List[PlaythroughPublic]


class TeacherPlaythroughQuery(BaseModel):
    class_id: Optional[int] = None
    scenario_code: Optional[str] = None
    status: Optional[str] = None
