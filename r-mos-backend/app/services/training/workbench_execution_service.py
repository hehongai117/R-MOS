from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import SessionStepRecord
from app.schemas.evidence import (
    EvidenceBundleCreate,
    EvidenceBundleType,
    EvidenceItem,
    EvidenceType,
    HashAlgo,
)
from app.services.evidence_service import EvidenceService
from app.services.llm import LLMProvider, llm_router
from app.services.training.session_service import SessionService
from app.services.training.submission_service import SubmissionService
from app.services.user_preference_service import UserPreferenceService


class TrainingWorkbenchExecutionService:
    """训练工作台执行态服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = SessionService(db)
        self.evidence_service = EvidenceService(db)
        self.preference_service = UserPreferenceService(db)
        self.storage_root = Path(__file__).resolve().parents[3] / "storage" / "training-evidence"

    async def upload_evidence(
        self,
        *,
        user_id: int,
        session_id: str,
        step_id: str,
        note: str,
        file: UploadFile,
    ) -> dict[str, Any]:
        session = await self._get_owned_session(user_id, session_id)
        step_meta = self._get_step_meta(session.project_snapshot, step_id)

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="证据文件为空")

        filename = Path(file.filename or "evidence.bin").name
        stored_name = f"{uuid4().hex[:8]}-{filename}"
        target_dir = self.storage_root / session_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / stored_name
        target_path.write_bytes(content)

        content_hash = hashlib.sha256(content).hexdigest()
        now = datetime.now(timezone.utc)
        content_uri = f"local://training-evidence/{session_id}/{stored_name}"
        bundle = await self.evidence_service.create_bundle(
            EvidenceBundleCreate(
                bundle_type=EvidenceBundleType.MEDIA,
                observed_time_start=now,
                observed_time_end=now,
                human_summary=note or f"{step_meta.get('title', step_id)} 证据",
                machine_tags=["training-workbench", session_id, step_id],
                items=[
                    EvidenceItem(
                        evidence_id=str(uuid4()),
                        evidence_type=EvidenceType.MEDIA,
                        content_uri=content_uri,
                        content_hash=content_hash,
                        content_hash_algo=HashAlgo.SHA256,
                        content_mime_type=file.content_type or "application/octet-stream",
                        size_bytes=len(content),
                        observed_time=now,
                        ingest_time=now,
                        human_summary=note or filename,
                        machine_code=step_id,
                        machine_tags=[session_id, step_id, filename],
                    )
                ],
            )
        )

        return {
            "evidence_bundle_id": bundle.evidence_bundle_id,
            "filename": filename,
            "content_uri": content_uri,
            "human_summary": bundle.human_summary,
        }

    async def submit_step(
        self,
        *,
        user_id: int,
        session_id: str,
        step_id: str,
        step_index: int,
        note: str,
        evidence_bundle_id: str | None,
        tools_confirmed: list[dict[str, Any]],
    ) -> dict[str, Any]:
        session = await self._get_owned_session(user_id, session_id)
        step_meta = self._get_step_meta(session.project_snapshot, step_id)
        record = await self._get_step_record(session_id, step_id)

        critical_ids = {
            str(tool.get("id"))
            for tool in step_meta.get("tools", [])
            if bool(tool.get("is_critical"))
        }
        confirmed_ids = {
            str(tool.get("tool_id"))
            for tool in tools_confirmed
            if str(tool.get("status", "")).upper() == "CONFIRMED"
        }
        anomaly_ids = [
            str(tool.get("tool_id"))
            for tool in tools_confirmed
            if str(tool.get("status", "")).upper() == "ANOMALY"
        ]
        missing_critical = sorted(tool_id for tool_id in critical_ids if tool_id not in confirmed_ids)
        has_evidence = bool(evidence_bundle_id)
        passed = has_evidence and not missing_critical and not anomaly_ids

        summary = (
            "关键工具已确认且证据已入库，可以继续下一步。"
            if passed
            else "仍缺少关键工具确认或证据，建议补齐后再提交。"
        )
        details = await self._generate_verdict_explanation(
            session=session,
            step_meta=step_meta,
            note=note,
            tools_confirmed=tools_confirmed,
            evidence_bundle_id=evidence_bundle_id,
            passed=passed,
            missing_critical=missing_critical,
            anomaly_ids=anomaly_ids,
        )

        verdict = {
            "result": "PASS" if passed else "FAIL",
            "summary": summary,
            "details": details,
            "missing_critical_tools": missing_critical,
            "anomaly_tools": anomaly_ids,
            "evidence_bundle_id": evidence_bundle_id,
        }

        record_id = await self.session_service.update_step(
            session_id=session_id,
            step_id=step_id,
            step_index=step_index,
            status="pass" if passed else "fail",
            attempt_count=(record.attempt_count if record else 0) + 1,
            tools_confirmed=tools_confirmed,
            evidence={
                "bundle_id": evidence_bundle_id,
                "note": note,
            },
            verdict_result=verdict,
            duration_sec=step_meta.get("duration_sec"),
        )

        session_submitted = False
        feedback = None
        check_result = await SubmissionService(self.db).check_submit_ready(session_id)
        if check_result.can_submit and not check_result.incomplete_steps:
            submission = await SubmissionService(self.db).submit_manual(
                session_id=session_id,
                user_id=user_id,
                confirm_incomplete=True,
            )
            session_submitted = submission is not None
            if submission is not None:
                feedback = {
                    "submission_id": submission.submission_id,
                    "score": submission.payload.get("score"),
                }

        next_step_id = self._resolve_next_step_id(session.project_snapshot, step_id)
        return {
            "record_id": record_id,
            "status": "pass" if passed else "fail",
            "verdict": verdict,
            "next_step_id": next_step_id,
            "session_submitted": session_submitted,
            "feedback": feedback,
            "evidence_bundle_id": evidence_bundle_id,
        }

    async def ask_follow_up(
        self,
        *,
        user_id: int,
        session_id: str,
        step_id: str,
        question: str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        session = await self._get_owned_session(user_id, session_id)
        step_meta = self._get_step_meta(session.project_snapshot, step_id)
        llm_pref = await self._get_llm_preference(user_id)
        prompt = self._build_follow_up_prompt(
            session_id=session_id,
            step_meta=step_meta,
            question=question,
            messages=messages,
        )
        response = await llm_router.chat(
            messages=[{"role": "user", "content": prompt}],
            provider=self._map_provider(llm_pref["provider"]),
            model=llm_pref["model"],
            temperature=0.4,
            max_tokens=800,
            api_key=llm_pref["api_key"],
            base_url=llm_pref["base_url"] or None,
        )
        return {
            "id": f"assistant-{uuid4().hex[:8]}",
            "role": "assistant",
            "content": self._strip_reasoning_blocks(response.content)
            or "请先确认关键工具状态与现场证据，再继续执行下一步。",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _get_owned_session(self, user_id: int, session_id: str):
        session = await self.session_service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Session access denied")
        return session

    @staticmethod
    def _get_step_meta(project_snapshot: dict | None, step_id: str) -> dict[str, Any]:
        for step in (project_snapshot or {}).get("steps", []):
            if str(step.get("id")) == step_id:
                return dict(step)
        raise HTTPException(status_code=404, detail="Step metadata not found")

    async def _get_step_record(self, session_id: str, step_id: str) -> SessionStepRecord | None:
        result = await self.db.execute(
            select(SessionStepRecord).where(
                SessionStepRecord.session_id == session_id,
                SessionStepRecord.step_id == step_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_llm_preference(self, user_id: int) -> dict[str, str]:
        pref = await self.preference_service.get_or_create_preference(user_id)
        llm = dict((pref.preferences or {}).get("llm") or {})
        provider = str(llm.get("provider") or "").strip() or "openai"
        model = str(llm.get("model") or "").strip()
        api_key = str(llm.get("api_key") or "").strip()
        base_url = str(llm.get("base_url") or "").strip()
        if not model or not api_key:
            raise HTTPException(status_code=400, detail="当前账号尚未完成大模型配置，请先在设置页填写模型名称与 API Key")
        return {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
        }

    @staticmethod
    def _map_provider(provider: str) -> LLMProvider:
        normalized = provider.strip().lower()
        if normalized == LLMProvider.ANTHROPIC.value:
            return LLMProvider.ANTHROPIC
        if normalized == LLMProvider.OLLAMA.value:
            return LLMProvider.OLLAMA
        return LLMProvider.OPENAI

    async def _generate_verdict_explanation(
        self,
        *,
        session,
        step_meta: dict[str, Any],
        note: str,
        tools_confirmed: list[dict[str, Any]],
        evidence_bundle_id: str | None,
        passed: bool,
        missing_critical: list[str],
        anomaly_ids: list[str],
    ) -> str:
        llm_pref = await self._get_llm_preference(session.user_id)
        prompt = f"""
你是训练裁决助手。请基于以下上下文，给出 1 段中文裁决解释。

会话ID：{session.session_id}
步骤标题：{step_meta.get("title", "")}
步骤说明：{step_meta.get("instruction", "")}
学员备注：{note or "无"}
工具确认：{json.dumps(tools_confirmed, ensure_ascii=False)}
证据包：{evidence_bundle_id or "无"}
规则判定：{"PASS" if passed else "FAIL"}
缺失关键工具：{", ".join(missing_critical) or "无"}
异常工具：{", ".join(anomaly_ids) or "无"}

要求：
1. 如果规则判定为 FAIL，明确指出缺口。
2. 如果规则判定为 PASS，说明为什么可以继续。
3. 不要输出 Markdown。
        """.strip()
        response = await llm_router.chat(
            messages=[{"role": "user", "content": prompt}],
            provider=self._map_provider(llm_pref["provider"]),
            model=llm_pref["model"],
            temperature=0.2,
            max_tokens=500,
            api_key=llm_pref["api_key"],
            base_url=llm_pref["base_url"] or None,
        )
        return self._strip_reasoning_blocks(response.content) or (
            "关键工具与证据均满足要求，可以进入下一步。" if passed else "当前不满足提交条件，请补齐关键工具和证据。"
        )

    @staticmethod
    def _resolve_next_step_id(project_snapshot: dict | None, step_id: str) -> str | None:
        steps = list((project_snapshot or {}).get("steps", []))
        for index, step in enumerate(steps):
            if str(step.get("id")) == step_id:
                return str(steps[index + 1].get("id")) if index + 1 < len(steps) else None
        return None

    @staticmethod
    def _build_follow_up_prompt(
        *,
        session_id: str,
        step_meta: dict[str, Any],
        question: str,
        messages: list[dict[str, Any]],
    ) -> str:
        return f"""
你是训练工作台的 AI 助手，请结合当前步骤上下文回答学员问题。

会话ID：{session_id}
步骤标题：{step_meta.get("title", "")}
步骤说明：{step_meta.get("instruction", "")}
证据提示：{step_meta.get("evidence_hint", "")}
工具列表：{json.dumps(step_meta.get("tools", []), ensure_ascii=False)}
最近消息：{json.dumps(messages[-5:], ensure_ascii=False)}
学员问题：{question}

要求：
1. 用中文回答。
2. 优先给执行建议，不讲空话。
3. 如果问题与当前步骤风险相关，先提醒安全前置条件。
        """.strip()

    @staticmethod
    def _strip_reasoning_blocks(content: str) -> str:
        sanitized = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE)
        return sanitized.strip()
