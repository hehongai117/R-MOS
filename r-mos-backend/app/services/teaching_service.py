"""
Teaching domain service layer (Phase 1).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Union
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolation, ResourceNotFoundError
from app.models.teaching import (
    GuidancePolicy,
    TeachingClass,
    Course,
    Enrollment,
    Assignment,
    AssignmentAttempt,
    EvidenceLink,
)


class TeachingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- Guidance Policies ----
    async def create_guidance_policy(
        self,
        *,
        name: str,
        base_mode: str = "teaching",
        allow_ghost_hand: bool = True,
        allow_hint_button: bool = True,
        show_error_details: bool = True,
        max_retry_count: int = -1,
        description: Optional[str] = None,
    ) -> GuidancePolicy:
        policy = GuidancePolicy(
            name=name,
            base_mode=base_mode,
            allow_ghost_hand=allow_ghost_hand,
            allow_hint_button=allow_hint_button,
            show_error_details=show_error_details,
            max_retry_count=max_retry_count,
            description=description,
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def list_guidance_policies(self) -> List[GuidancePolicy]:
        result = await self.db.execute(select(GuidancePolicy).order_by(GuidancePolicy.id))
        return result.scalars().all()

    async def get_guidance_policy(self, policy_id: int) -> GuidancePolicy:
        result = await self.db.execute(select(GuidancePolicy).where(GuidancePolicy.id == policy_id))
        policy = result.scalar_one_or_none()
        if not policy:
            raise ResourceNotFoundError("GuidancePolicy", policy_id)
        return policy

    # ---- Classes / Courses / Enrollments ----
    async def create_class(
        self,
        *,
        name: str,
        term: Optional[str] = None,
        teacher_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> TeachingClass:
        teaching_class = TeachingClass(
            name=name,
            term=term,
            teacher_id=teacher_id,
            metadata_json=metadata,
        )
        self.db.add(teaching_class)
        await self.db.commit()
        await self.db.refresh(teaching_class)
        return teaching_class

    async def list_classes(self, *, school_name: str | None = None) -> List[TeachingClass]:
        """列出班级；`school_name` 非空时只返回该校班级。

        `classes` 表本身没有学校维度，学校经班主任推导
        （`TeachingClass.teacher_id` → `User.school_name`）。
        `school_name` 为 None 表示不过滤——仅管理员走该分支。
        """
        stmt = select(TeachingClass).order_by(TeachingClass.id)
        if school_name is not None:
            from app.models.user import User

            stmt = stmt.join(User, User.id == TeachingClass.teacher_id).where(
                User.school_name == school_name
            )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_class(self, class_id: int) -> TeachingClass:
        result = await self.db.execute(select(TeachingClass).where(TeachingClass.id == class_id))
        teaching_class = result.scalar_one_or_none()
        if not teaching_class:
            raise ResourceNotFoundError("Class", class_id)
        return teaching_class

    async def update_class(
        self,
        class_id: int,
        *,
        name: Optional[str] = None,
        term: Optional[str] = None,
        teacher_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> TeachingClass:
        teaching_class = await self.get_class(class_id)
        if name is not None:
            teaching_class.name = name
        if term is not None:
            teaching_class.term = term
        if teacher_id is not None:
            teaching_class.teacher_id = teacher_id
        if metadata is not None:
            teaching_class.metadata_json = metadata

        await self.db.commit()
        await self.db.refresh(teaching_class)
        return teaching_class

    async def create_course(
        self,
        *,
        class_id: int,
        name: str,
        description: Optional[str] = None,
        schedule: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Course:
        await self._ensure_class_exists(class_id)
        course = Course(
            class_id=class_id,
            name=name,
            description=description,
            schedule=schedule,
            metadata_json=metadata,
        )
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        return course

    async def list_courses(self, *, class_id: Optional[int] = None) -> List[Course]:
        query = select(Course)
        if class_id is not None:
            query = query.where(Course.class_id == class_id)
        result = await self.db.execute(query.order_by(Course.id))
        return result.scalars().all()

    async def get_course(self, course_id: int) -> Course:
        result = await self.db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if not course:
            raise ResourceNotFoundError("Course", course_id)
        return course

    async def enroll_student(
        self,
        *,
        class_id: int,
        student_id: int,
        role: str = "student",
    ) -> Enrollment:
        await self._ensure_class_exists(class_id)
        result = await self.db.execute(
            select(Enrollment).where(
                Enrollment.class_id == class_id,
                Enrollment.student_id == student_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise BusinessRuleViolation(
                message="学生已在班级中",
                code="ALREADY_ENROLLED",
                details={"class_id": class_id, "student_id": student_id},
            )

        enrollment = Enrollment(class_id=class_id, student_id=student_id, role=role)
        self.db.add(enrollment)
        await self.db.commit()
        await self.db.refresh(enrollment)
        return enrollment

    async def list_enrollments(self, *, class_id: Optional[int] = None) -> List[Enrollment]:
        query = select(Enrollment)
        if class_id is not None:
            query = query.where(Enrollment.class_id == class_id)
        result = await self.db.execute(query.order_by(Enrollment.id))
        return result.scalars().all()

    # ---- Assignments / Attempts ----
    async def create_assignment(
        self,
        *,
        class_id: int,
        title: str,
        course_id: Optional[int] = None,
        sop_id: Optional[int] = None,
        guidance_policy_id: Optional[int] = None,
        start_at: Optional[datetime] = None,
        due_at: Optional[datetime] = None,
        max_attempts: int = 1,
        scoring_policy: Optional[dict] = None,
        competition_mode: bool = False,
        hidden_sop: bool = False,
        blind_step_mask: Optional[dict] = None,
    ) -> Assignment:
        await self._ensure_class_exists(class_id)
        assignment = Assignment(
            class_id=class_id,
            course_id=course_id,
            title=title,
            sop_id=sop_id,
            guidance_policy_id=guidance_policy_id,
            start_at=start_at,
            due_at=due_at,
            max_attempts=max_attempts,
            scoring_policy=scoring_policy,
            competition_mode=competition_mode,
            hidden_sop=hidden_sop,
            blind_step_mask=blind_step_mask,
        )
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def list_assignments(self, *, class_id: Optional[int] = None) -> List[Assignment]:
        query = select(Assignment)
        if class_id is not None:
            query = query.where(Assignment.class_id == class_id)
        result = await self.db.execute(query.order_by(Assignment.id))
        return result.scalars().all()

    async def get_assignment(self, assignment_id: int) -> Assignment:
        result = await self.db.execute(select(Assignment).where(Assignment.id == assignment_id))
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise ResourceNotFoundError("Assignment", assignment_id)
        return assignment

    async def create_attempt(
        self,
        *,
        assignment_id: int,
        student_id: int,
        task_id: Optional[int] = None,
    ) -> AssignmentAttempt:
        await self.get_assignment(assignment_id)
        max_index_result = await self.db.execute(
            select(func.max(AssignmentAttempt.attempt_index)).where(
                AssignmentAttempt.assignment_id == assignment_id,
                AssignmentAttempt.student_id == student_id,
            )
        )
        max_index = max_index_result.scalar() or 0
        attempt = AssignmentAttempt(
            assignment_id=assignment_id,
            student_id=student_id,
            task_id=task_id,
            attempt_index=max_index + 1,
            status="in_progress",
        )
        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def get_attempt(self, attempt_id: int) -> AssignmentAttempt:
        result = await self.db.execute(select(AssignmentAttempt).where(AssignmentAttempt.id == attempt_id))
        attempt = result.scalar_one_or_none()
        if not attempt:
            raise ResourceNotFoundError("AssignmentAttempt", attempt_id)
        return attempt

    async def list_attempts(self, *, assignment_id: int) -> List[AssignmentAttempt]:
        await self.get_assignment(assignment_id)
        result = await self.db.execute(
            select(AssignmentAttempt)
            .where(AssignmentAttempt.assignment_id == assignment_id)
            .order_by(AssignmentAttempt.attempt_index)
        )
        return result.scalars().all()

    async def update_attempt_status(
        self,
        attempt_id: int,
        new_status: Union[str, Enum],
    ) -> AssignmentAttempt:
        attempt = await self.get_attempt(attempt_id)
        normalized = self._normalize_status(new_status)
        if not self._is_valid_transition(attempt.status, normalized):
            raise BusinessRuleViolation(
                message="不允许的状态转换",
                code="INVALID_ATTEMPT_STATUS_TRANSITION",
                details={"from": attempt.status, "to": normalized},
            )
        attempt.status = normalized
        if normalized == "abandoned":
            attempt.abandoned_at = datetime.now(timezone.utc)
        if normalized == "completed":
            await self._build_attempt_timeline(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def _build_attempt_timeline(self, attempt: AssignmentAttempt) -> None:
        """尝试完成时，把它已有的证据链接落成一条多模态时间线。

        S1-001 §3.4 裁决二：时间线三表（`multimodal_timelines`／`timeline_segments`／
        `alignment_map`）此前**整组无应用写入路径**，裁定为「**先补写入再开放回放**」。
        本方法即该写入路径。

        **数据来源是该尝试真实的 `EvidenceLink`，不编造内容**——
        没有证据就不建时间线，回放继续如实返回 `insufficient_data`。
        这与「接口存在但能力不存在」相反：有多少证据就回放多少。

        幂等：同一 attempt 已有时间线时直接返回，不重复建。
        """
        from app.models.timeline import AlignmentMap, MultimodalTimeline, TimelineSegment

        existing = await self.db.execute(
            select(MultimodalTimeline.id).where(
                MultimodalTimeline.scope_type == "attempt",
                MultimodalTimeline.scope_id == str(attempt.id),
            )
        )
        if existing.scalar_one_or_none() is not None:
            return

        links_result = await self.db.execute(
            select(EvidenceLink)
            .where(EvidenceLink.attempt_id == attempt.id)
            .order_by(EvidenceLink.id)
        )
        links = list(links_result.scalars())
        if not links:
            return

        timeline = MultimodalTimeline(
            scope_type="attempt",
            scope_id=str(attempt.id),
            created_by_user_id=str(attempt.student_id),
        )
        self.db.add(timeline)
        await self.db.flush()

        for index, link in enumerate(links):
            segment = TimelineSegment(
                timeline_id=timeline.id,
                segment_type="evidence",
                ref_id=link.bundle_id,
                start_ts_ms=index * 1000,
                end_ts_ms=(index + 1) * 1000,
            )
            self.db.add(segment)
            await self.db.flush()
            self.db.add(
                AlignmentMap(
                    timeline_id=timeline.id,
                    anchor_key=f"evidence:{link.bundle_id}",
                    segment_id=segment.id,
                    ref_id=link.bundle_id,
                )
            )

    async def grade_attempt(self, attempt_id: int, *, score: float) -> AssignmentAttempt:
        attempt = await self.get_attempt(attempt_id)
        if attempt.status != "completed":
            raise BusinessRuleViolation(
                message="Attempt未完成，无法评分",
                code="ATTEMPT_NOT_COMPLETED",
                details={"status": attempt.status},
            )
        attempt.status = "graded"
        attempt.score = score
        attempt.graded_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    # ---- Internal helpers ----
    async def _ensure_class_exists(self, class_id: int) -> None:
        result = await self.db.execute(select(TeachingClass).where(TeachingClass.id == class_id))
        if result.scalar_one_or_none() is None:
            raise ResourceNotFoundError("Class", class_id)

    def _normalize_status(self, status: Union[str, Enum]) -> str:
        if isinstance(status, Enum):
            return status.value
        return status

    def _is_valid_transition(self, current: str, target: str) -> bool:
        allowed = {
            "in_progress": {"completed", "abandoned"},
            "completed": {"graded"},
            "graded": set(),
            "abandoned": set(),
        }
        return target in allowed.get(current, set())
