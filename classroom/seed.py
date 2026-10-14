# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from sqlalchemy import select

from classroom.auth import hash_password
from classroom.config import CLASSROOM_SEED_DEMO, classroom_enabled
from classroom.db import _init_models, session_scope

logger = logging.getLogger(__name__)

_DEMO_TEACHER_EMAIL = "teacher@demo.edu"
_DEMO_STUDENTS = [
    ("student1@demo.edu", "演示学生甲", "20250001"),
    ("student2@demo.edu", "演示学生乙", "20250002"),
]
_DEMO_PASSWORD = "demo1234"
_DEMO_CLASS_NAME = "2025 秋财税史演示班"


def seed_demo_data() -> None:
    if not classroom_enabled() or not CLASSROOM_SEED_DEMO:
        return
    UserRow, ClassRow, ClassMemberRow, _, _ = _init_models()
    with session_scope() as db:
        existing = db.execute(select(UserRow.id).where(UserRow.email == _DEMO_TEACHER_EMAIL)).scalar_one_or_none()
        if existing is not None:
            logger.info("classroom demo seed skipped (already exists)")
            return

        teacher = UserRow(
            email=_DEMO_TEACHER_EMAIL,
            password_hash=hash_password(_DEMO_PASSWORD),
            name="演示教师",
            role="teacher",
            org="local",
        )
        db.add(teacher)
        db.flush()

        students = []
        for email, name, sid in _DEMO_STUDENTS:
            row = UserRow(
                email=email,
                password_hash=hash_password(_DEMO_PASSWORD),
                name=name,
                role="student",
                org="local",
                student_id=sid,
            )
            db.add(row)
            db.flush()
            students.append(row)

        klass = ClassRow(
            name=_DEMO_CLASS_NAME,
            course_name="中国财税史",
            semester="2025-fall",
            teacher_user_id=teacher.id,
        )
        db.add(klass)
        db.flush()

        for student in students:
            db.add(ClassMemberRow(class_id=klass.id, user_id=student.id))

        logger.info(
            "classroom demo seed ok: teacher=%s students=%d class=%s",
            _DEMO_TEACHER_EMAIL,
            len(students),
            _DEMO_CLASS_NAME,
        )
