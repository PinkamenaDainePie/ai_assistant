# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import joinedload

from classroom.auth import create_access_token, hash_password, verify_password
from classroom.config import CLASSROOM_DEFAULT_CLASS_ID, CLASSROOM_SEED_DEMO
from classroom.db import _init_models, session_scope
from classroom.quarter_chapters import merge_quarter_chapters, resolve_playthrough_quarter_chapters
from classroom.schemas import (
    ClassInfo,
    PlaythroughCreate,
    PlaythroughPublic,
    PlaythroughReviewRequest,
    PlaythroughUpdate,
    UserPublic,
)


def _user_public(row: Any) -> UserPublic:
    return UserPublic(
        id=row.id,
        email=row.email,
        name=row.name,
        role=row.role,
        org=row.org,
        student_id=row.student_id,
    )


def _playthrough_public(
    row: Any,
    *,
    student_name: Optional[str] = None,
    student_id: Optional[str] = None,
    review: Optional[Any] = None,
    include_quarter_chapters: bool = False,
) -> PlaythroughPublic:
    return PlaythroughPublic(
        id=row.id,
        user_id=row.user_id,
        scenario_code=row.scenario_code,
        game_session_id=row.game_session_id,
        status=row.status,
        current_quarter=row.current_quarter,
        ending_type=row.ending_type,
        summary_json=row.summary_json or {},
        started_at=row.started_at,
        finished_at=row.finished_at,
        student_name=student_name,
        student_id=student_id,
        teacher_review_score=int(review.score) if review is not None else None,
        teacher_review_comment=(review.comment or None) if review is not None else None,
        teacher_review_at=review.updated_at if review is not None else None,
        quarter_chapters=resolve_playthrough_quarter_chapters(row) if include_quarter_chapters else [],
    )


def _load_reviews_map(db: Any, playthrough_ids: List[UUID]) -> Dict[UUID, Any]:
    if not playthrough_ids:
        return {}
    _, _, _, _, PlaythroughReviewRow = _init_models()
    rows = db.execute(
        select(PlaythroughReviewRow).where(PlaythroughReviewRow.playthrough_id.in_(playthrough_ids))
    ).scalars().all()
    return {r.playthrough_id: r for r in rows}


def _assert_teacher_playthrough_access(db: Any, teacher_id: UUID, playthrough_id: UUID) -> Any:
    _, ClassRow, ClassMemberRow, PlaythroughRow, _ = _init_models()
    row = db.get(PlaythroughRow, playthrough_id)
    if row is None:
        raise HTTPException(status_code=404, detail="游玩记录不存在")
    in_class = db.execute(
        select(ClassMemberRow.class_id)
        .join(ClassRow, ClassRow.id == ClassMemberRow.class_id)
        .where(
            ClassMemberRow.user_id == row.user_id,
            ClassRow.teacher_user_id == teacher_id,
        )
    ).first()
    if in_class is None:
        raise HTTPException(status_code=403, detail="无权查看该记录")
    return row


def _raise_db_unavailable(exc: Exception) -> None:
    raise HTTPException(
        status_code=503,
        detail="课堂数据库不可用：请检查 DATABASE_URL、网络/VPN，或腾讯云 PostgreSQL 实例是否在线",
    ) from exc


def login_user(email: str, password: str) -> Dict[str, Any]:
    UserRow, _, _, _, _ = _init_models()
    normalized = email.strip().lower()
    try:
        with session_scope() as db:
            row = db.execute(select(UserRow).where(UserRow.email == normalized)).scalar_one_or_none()
            if row is None or not verify_password(password, row.password_hash):
                raise HTTPException(status_code=401, detail="邮箱或密码错误")
            token = create_access_token(user_id=row.id, role=row.role, org=row.org, name=row.name)
            return {"access_token": token, "user": _user_public(row)}
    except OperationalError as exc:
        _raise_db_unavailable(exc)


def _auto_join_student_class(db: Any, user_id: UUID, role: str) -> None:
    if role != "student":
        return
    _, ClassRow, ClassMemberRow, _, _ = _init_models()
    class_id = CLASSROOM_DEFAULT_CLASS_ID
    if class_id <= 0 and CLASSROOM_SEED_DEMO:
        class_id = db.execute(select(ClassRow.id).order_by(ClassRow.id).limit(1)).scalar_one_or_none() or 0
    if class_id <= 0:
        return
    exists = db.execute(
        select(ClassMemberRow.class_id).where(
            ClassMemberRow.class_id == class_id,
            ClassMemberRow.user_id == user_id,
        )
    ).scalar_one_or_none()
    if exists is not None:
        return
    db.add(ClassMemberRow(class_id=class_id, user_id=user_id))


def register_user(
    *,
    email: str,
    password: str,
    name: str,
    role: str,
    student_id: Optional[str],
) -> UserPublic:
    UserRow, _, _, _, _ = _init_models()
    normalized = email.strip().lower()
    with session_scope() as db:
        exists = db.execute(select(UserRow.id).where(UserRow.email == normalized)).scalar_one_or_none()
        if exists is not None:
            raise HTTPException(status_code=409, detail="该邮箱已注册")
        row = UserRow(
            email=normalized,
            password_hash=hash_password(password),
            name=name.strip(),
            role=role,
            org="local",
            student_id=(student_id or "").strip() or None,
        )
        db.add(row)
        db.flush()
        _auto_join_student_class(db, row.id, role)
        return _user_public(row)


def get_user_by_id(user_id: UUID) -> UserPublic:
    UserRow, _, _, _, _ = _init_models()
    with session_scope() as db:
        row = db.get(UserRow, user_id)
        if row is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        return _user_public(row)


def upsert_swufe_user(
    *,
    swufe_id: str,
    email: str,
    name: str,
    role: str,
    student_id: Optional[str],
) -> Dict[str, Any]:
    UserRow, ClassRow, ClassMemberRow, _, _ = _init_models()
    normalized_email = email.strip().lower()
    sid = (student_id or "").strip() or None
    with session_scope() as db:
        row = None
        if swufe_id:
            row = db.execute(select(UserRow).where(UserRow.swufe_id == swufe_id)).scalar_one_or_none()
        if row is None:
            row = db.execute(select(UserRow).where(UserRow.email == normalized_email)).scalar_one_or_none()
        if row is None:
            row = UserRow(
                email=normalized_email,
                password_hash="",
                name=name.strip() or "财大用户",
                role=role,
                org="swufe",
                swufe_id=swufe_id or None,
                student_id=sid,
            )
            db.add(row)
        else:
            row.email = normalized_email
            row.name = name.strip() or row.name
            row.org = "swufe"
            if swufe_id:
                row.swufe_id = swufe_id
            if sid:
                row.student_id = sid
            if role == "teacher":
                row.role = "teacher"
            elif row.role not in ("teacher", "admin"):
                row.role = role
        db.flush()
        if role == "teacher":
            has_class = db.execute(
                select(ClassRow.id).where(ClassRow.teacher_user_id == row.id)
            ).first()
            if has_class is None:
                db.add(
                    ClassRow(
                        name=f"{row.name}的班级",
                        course_name="中国财税史",
                        semester="",
                        teacher_user_id=row.id,
                    )
                )
                db.flush()
        if role == "student":
            target_class_id = CLASSROOM_DEFAULT_CLASS_ID
            if target_class_id <= 0:
                classes = db.execute(select(ClassRow.id).limit(2)).scalars().all()
                if len(classes) == 1:
                    target_class_id = int(classes[0])
            if target_class_id > 0:
                exists = db.execute(
                    select(ClassMemberRow.class_id).where(
                        ClassMemberRow.class_id == target_class_id,
                        ClassMemberRow.user_id == row.id,
                    )
                ).scalar_one_or_none()
                if exists is None:
                    klass = db.get(ClassRow, target_class_id)
                    if klass is not None:
                        db.add(ClassMemberRow(class_id=klass.id, user_id=row.id))
        token = create_access_token(user_id=row.id, role=row.role, org=row.org, name=row.name)
        return {"access_token": token, "user": _user_public(row)}


def list_teacher_classes(teacher_id: UUID) -> List[ClassInfo]:
    _, ClassRow, _, _, _ = _init_models()
    with session_scope() as db:
        rows = db.execute(
            select(ClassRow).where(ClassRow.teacher_user_id == teacher_id).order_by(ClassRow.id)
        ).scalars().all()
        return [
            ClassInfo(id=r.id, name=r.name, course_name=r.course_name, semester=r.semester) for r in rows
        ]


def create_playthrough(user_id: UUID, body: PlaythroughCreate) -> PlaythroughPublic:
    _, _, _, PlaythroughRow, _ = _init_models()
    with session_scope() as db:
        row = PlaythroughRow(
            user_id=user_id,
            scenario_code=body.scenario_code.strip(),
            game_session_id=body.game_session_id.strip(),
            campaign_session_id=(body.campaign_session_id or "").strip() or None,
            status="in_progress",
            current_quarter=0,
            summary_json={},
            quarter_chapters_json=[],
        )
        db.add(row)
        db.flush()
        return _playthrough_public(row, include_quarter_chapters=True)


def update_playthrough(user_id: UUID, playthrough_id: UUID, body: PlaythroughUpdate) -> PlaythroughPublic:
    _, _, _, PlaythroughRow, _ = _init_models()
    with session_scope() as db:
        row = db.get(PlaythroughRow, playthrough_id)
        if row is None or row.user_id != user_id:
            raise HTTPException(status_code=404, detail="游玩记录不存在")
        if body.status is not None:
            row.status = body.status
            if body.status == "finished" and row.finished_at is None:
                row.finished_at = datetime.now(timezone.utc)
        if body.current_quarter is not None:
            row.current_quarter = body.current_quarter
        if body.ending_type is not None:
            row.ending_type = body.ending_type
        if body.summary_json is not None:
            row.summary_json = body.summary_json
        if body.campaign_session_id and not (row.campaign_session_id or "").strip():
            row.campaign_session_id = body.campaign_session_id.strip()
        if body.quarter_chapters is not None:
            row.quarter_chapters_json = merge_quarter_chapters(
                row.quarter_chapters_json,
                body.quarter_chapters,
            )
        db.flush()
        return _playthrough_public(row, include_quarter_chapters=True)


def list_my_playthroughs(user_id: UUID) -> List[PlaythroughPublic]:
    _, _, _, PlaythroughRow, _ = _init_models()
    with session_scope() as db:
        rows = db.execute(
            select(PlaythroughRow)
            .where(PlaythroughRow.user_id == user_id)
            .order_by(PlaythroughRow.started_at.desc())
        ).scalars().all()
        return [_playthrough_public(r) for r in rows]


def get_my_playthrough(user_id: UUID, playthrough_id: UUID) -> PlaythroughPublic:
    _, _, _, PlaythroughRow, _ = _init_models()
    with session_scope() as db:
        row = db.get(PlaythroughRow, playthrough_id)
        if row is None or row.user_id != user_id:
            raise HTTPException(status_code=404, detail="游玩记录不存在")
        return _playthrough_public(row, include_quarter_chapters=True)


def _teacher_class_ids(db: Any, teacher_id: UUID, class_id: Optional[int]) -> List[int]:
    _, ClassRow, _, _, _ = _init_models()
    q = select(ClassRow.id).where(ClassRow.teacher_user_id == teacher_id)
    if class_id is not None:
        q = q.where(ClassRow.id == class_id)
    ids = list(db.execute(q).scalars().all())
    if class_id is not None and not ids:
        raise HTTPException(status_code=403, detail="无权访问该班级")
    return ids


def list_teacher_playthroughs(
    teacher_id: UUID,
    *,
    class_id: Optional[int] = None,
    scenario_code: Optional[str] = None,
    status: Optional[str] = None,
) -> List[PlaythroughPublic]:
    UserRow, _, ClassMemberRow, PlaythroughRow, _ = _init_models()
    with session_scope() as db:
        class_ids = _teacher_class_ids(db, teacher_id, class_id)
        if not class_ids:
            return []
        member_ids = db.execute(
            select(ClassMemberRow.user_id).where(ClassMemberRow.class_id.in_(class_ids))
        ).scalars().all()
        if not member_ids:
            return []
        q = (
            select(PlaythroughRow, UserRow)
            .join(UserRow, UserRow.id == PlaythroughRow.user_id)
            .where(PlaythroughRow.user_id.in_(member_ids))
            .order_by(PlaythroughRow.started_at.desc())
        )
        if scenario_code:
            q = q.where(PlaythroughRow.scenario_code == scenario_code.strip())
        if status:
            q = q.where(PlaythroughRow.status == status.strip())
        rows = db.execute(q).all()
        review_map = _load_reviews_map(db, [pt.id for pt, _user in rows])
        return [
            _playthrough_public(
                pt,
                student_name=user.name,
                student_id=user.student_id,
                review=review_map.get(pt.id),
            )
            for pt, user in rows
        ]


def get_teacher_playthrough(teacher_id: UUID, playthrough_id: UUID) -> PlaythroughPublic:
    UserRow, _, _, PlaythroughRow, PlaythroughReviewRow = _init_models()
    with session_scope() as db:
        row = _assert_teacher_playthrough_access(db, teacher_id, playthrough_id)
        user = db.get(UserRow, row.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="游玩记录不存在")
        review = db.get(PlaythroughReviewRow, playthrough_id)
        return _playthrough_public(
            row,
            student_name=user.name,
            student_id=user.student_id,
            review=review,
            include_quarter_chapters=True,
        )


def upsert_teacher_playthrough_review(
    teacher_id: UUID,
    playthrough_id: UUID,
    body: PlaythroughReviewRequest,
) -> PlaythroughPublic:
    UserRow, _, _, PlaythroughRow, PlaythroughReviewRow = _init_models()
    with session_scope() as db:
        row = _assert_teacher_playthrough_access(db, teacher_id, playthrough_id)
        user = db.get(UserRow, row.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="游玩记录不存在")
        review = db.get(PlaythroughReviewRow, playthrough_id)
        comment = (body.comment or "").strip()
        if review is None:
            review = PlaythroughReviewRow(
                playthrough_id=playthrough_id,
                teacher_user_id=teacher_id,
                score=body.score,
                comment=comment,
            )
            db.add(review)
        else:
            if review.teacher_user_id != teacher_id:
                raise HTTPException(status_code=403, detail="仅原评语教师可修改")
            review.score = body.score
            review.comment = comment
            review.updated_at = datetime.now(timezone.utc)
        db.flush()
        return _playthrough_public(
            row,
            student_name=user.name,
            student_id=user.student_id,
            review=review,
            include_quarter_chapters=True,
        )
