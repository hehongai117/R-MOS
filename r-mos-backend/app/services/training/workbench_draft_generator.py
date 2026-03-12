"""
训练工作台草案生成器。

使用当前用户保存的 LLM 偏好，为空态训练工作台生成可直接展示的演示草案。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import LLMProvider, llm_router
from app.services.user_preference_service import UserPreferenceService


class TrainingWorkbenchDraftGenerator:
    """基于用户级 LLM 配置生成训练工作台草案。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.preference_service = UserPreferenceService(db)

    async def generate(
        self,
        *,
        user_id: int,
        robot_model: str,
        task_summary: str,
        focus_prompt: str,
    ) -> dict:
        llm_pref = await self._get_llm_preference(user_id)
        response = await llm_router.chat(
            messages=[{"role": "user", "content": self._build_prompt(robot_model, task_summary, focus_prompt)}],
            provider=self._map_provider(llm_pref["provider"]),
            model=llm_pref["model"],
            temperature=0.4,
            max_tokens=1800,
            api_key=llm_pref["api_key"],
            base_url=llm_pref["base_url"] or None,
        )
        normalized_content = self._strip_reasoning_blocks(response.content)
        try:
            payload = self._parse_response(normalized_content)
        except json.JSONDecodeError:
            payload = self._build_fallback_payload(
                robot_model=robot_model,
                task_summary=task_summary,
                focus_prompt=focus_prompt,
                llm_text=normalized_content,
            )
        return self._normalize_payload(payload, robot_model=robot_model, task_summary=task_summary)

    async def _get_llm_preference(self, user_id: int) -> dict[str, str]:
        pref = await self.preference_service.get_or_create_preference(user_id)
        llm = dict((pref.preferences or {}).get("llm") or {})

        provider = str(llm.get("provider") or "").strip() or "openai"
        model = str(llm.get("model") or "").strip()
        api_key = str(llm.get("api_key") or "").strip()
        base_url = str(llm.get("base_url") or "").strip()

        if not model or not api_key:
            raise ValueError("当前账号尚未完成大模型配置，请先在设置页填写模型名称与 API Key")

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

    @staticmethod
    def _build_prompt(robot_model: str, task_summary: str, focus_prompt: str) -> str:
        return f"""
你是机器人训练编排助手。请为训练工作台生成一个可直接展示的训练草案。

机器人型号：{robot_model}
训练任务：{task_summary}
额外要求：{focus_prompt}

返回 JSON，不要输出 Markdown 代码块，不要解释。
JSON 结构必须满足：
{{
  "project": {{
    "title": "训练标题",
    "summary": "一句话摘要"
  }},
      "steps": [
        {{
          "id": "step_prepare",
          "title": "步骤标题",
          "instruction": "该步骤操作说明",
          "evidence_hint": "本步骤建议上传什么证据",
          "model_targets": ["需要高亮的模型 link 名称"],
          "tools": [
            {{
              "name": "工具名称",
              "spec": "规格或确认点",
          "is_critical": true,
          "recommendation": "若异常时 AI 给出的补充建议，可为空"
        }}
      ]
    }}
  ],
  "messages": [
    {{
      "role": "assistant",
      "content": "AI 助手给学员的提示"
    }},
    {{
      "role": "teacher",
      "content": "教师提示或审核点"
    }}
  ]
}}

约束：
1. 生成 3 到 5 个步骤。
2. 每个步骤至少 2 个工具，其中至少 1 个关键工具。
3. 文案使用中文，适合训练场景。
4. 重点体现步骤编排、工具确认、证据上传、AI 提示。
5. 如果是 ATOM01，请优先使用这些 link 名称作为 model_targets：torso_link、left_knee_link、right_knee_link、left_ankle_pitch_link、right_ankle_pitch_link、left_arm_pitch_link、right_arm_pitch_link。
        """.strip()

    @staticmethod
    def _parse_response(content: str) -> dict:
        normalized = content.strip()
        normalized = re.sub(r"^```(?:json)?\s*", "", normalized)
        normalized = re.sub(r"\s*```$", "", normalized)
        return json.loads(normalized)

    @staticmethod
    def _strip_reasoning_blocks(content: str) -> str:
        sanitized = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE)
        return sanitized.strip()

    def _build_fallback_payload(
        self,
        *,
        robot_model: str,
        task_summary: str,
        focus_prompt: str,
        llm_text: str,
    ) -> dict:
        assistant_text = llm_text.strip() or "请先确认现场安全、工具状态与证据留存要求。"
        return {
            "project": {
                "title": f"{robot_model} {task_summary}",
                "summary": f"围绕 {task_summary} 的演示训练草案，重点覆盖 {focus_prompt}。",
            },
            "steps": [
                {
                    "id": "draft_prepare",
                    "title": "步骤 1: 准备工位",
                    "instruction": "确认断电挂牌、PPE 穿戴和工位清洁，建立本次训练的安全基线。",
                    "evidence_hint": "上传工位全景和断电挂牌照片。",
                    "model_targets": ["torso_link"],
                    "tools": [
                        {"name": "绝缘手套", "spec": "A级绝缘", "is_critical": True},
                        {"name": "扭矩扳手", "spec": "5-25Nm", "is_critical": True},
                    ],
                },
                {
                    "id": "draft_disassemble",
                    "title": "步骤 2: 执行拆装",
                    "instruction": f"围绕“{task_summary}”执行核心操作，逐项确认工具和零件状态。",
                    "evidence_hint": "上传关键拆装动作照片与零件摆位截图。",
                    "model_targets": [self._default_focus_target(task_summary)],
                    "tools": [
                        {"name": "六角扳手", "spec": "4mm", "is_critical": True},
                        {"name": "零件托盘", "spec": "分区托盘", "is_critical": False},
                    ],
                },
                {
                    "id": "draft_review",
                    "title": "步骤 3: 复核与提交",
                    "instruction": "复核扭矩、部件复位和风险点，整理证据后准备提交裁决。",
                    "evidence_hint": "上传复位结果、工具回收和最终状态截图。",
                    "model_targets": [self._default_focus_target(task_summary)],
                    "tools": [
                        {"name": "检查记录卡", "spec": "电子/纸质", "is_critical": False},
                        {"name": "检修灯", "spec": "无频闪", "is_critical": False},
                    ],
                },
            ],
            "messages": [
                {"role": "assistant", "content": assistant_text},
                {"role": "teacher", "content": "AI 返回了非结构化内容，系统已回退到安全草案模板，请重点核对步骤与工具。"},
            ],
        }

    def _normalize_payload(self, payload: dict, *, robot_model: str, task_summary: str) -> dict:
        project_payload = payload.get("project") or {}
        steps_payload = payload.get("steps") or []
        messages_payload = payload.get("messages") or []
        draft_session_id = f"draft-session-{uuid4().hex[:8]}"
        draft_project_id = f"draft-project-{uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()

        steps: list[dict] = []
        for index, raw_step in enumerate(steps_payload):
            step_id = str(raw_step.get("id") or f"draft-step-{index + 1}")
            tools = []
            for tool_index, raw_tool in enumerate(raw_step.get("tools") or []):
                tool_name = str(raw_tool.get("name") or f"工具 {tool_index + 1}")
                tools.append(
                    {
                        "id": f"{step_id}-tool-{tool_index + 1}",
                        "name": tool_name,
                        "spec": str(raw_tool.get("spec") or "待确认"),
                        "is_critical": bool(raw_tool.get("is_critical", tool_index == 0)),
                        "recommendation": raw_tool.get("recommendation"),
                    }
                )
            steps.append(
                {
                    "id": step_id,
                    "step_index": index,
                    "title": str(raw_step.get("title") or f"步骤 {index + 1}"),
                    "status": "active" if index == 0 else "pending",
                    "instruction": str(raw_step.get("instruction") or ""),
                    "evidence_hint": str(raw_step.get("evidence_hint") or "上传本步骤关键操作照片或截图。"),
                    "model_targets": self._normalize_model_targets(
                        raw_step.get("model_targets"),
                        title=str(raw_step.get("title") or ""),
                        instruction=str(raw_step.get("instruction") or ""),
                        task_summary=task_summary,
                    ),
                    "tools": tools,
                }
            )

        messages: list[dict] = []
        for index, raw_message in enumerate(messages_payload):
            role = str(raw_message.get("role") or "assistant")
            if role not in {"assistant", "teacher", "user"}:
                role = "assistant"
            messages.append(
                {
                    "id": f"draft-message-{index + 1}",
                    "role": role,
                    "content": str(raw_message.get("content") or ""),
                    "created_at": now,
                }
            )

        return {
            "project": {
                "session_id": draft_session_id,
                "project_id": draft_project_id,
                "title": str(project_payload.get("title") or f"{robot_model} {task_summary}"),
                "summary": str(project_payload.get("summary") or f"围绕 {task_summary} 生成的训练草案。"),
                "progress_percent": 0,
            },
            "steps": steps,
            "messages": messages,
        }

    @staticmethod
    def _default_focus_target(task_summary: str) -> str:
        mapping = {
            "髋": "left_thigh_pitch_link",
            "膝": "left_knee_link",
            "踝": "left_ankle_pitch_link",
            "肩": "left_arm_pitch_link",
            "肘": "left_elbow_pitch_link",
            "腕": "left_elbow_yaw_link",
            "关节电机盖": "left_knee_link",
        }
        for keyword, target in mapping.items():
            if keyword in task_summary:
                return target
        return "torso_link"

    def _normalize_model_targets(
        self,
        raw_targets: object,
        *,
        title: str,
        instruction: str,
        task_summary: str,
    ) -> list[str]:
        if isinstance(raw_targets, list):
            targets = [str(item).strip() for item in raw_targets if str(item).strip()]
            if targets:
                return targets

        combined = f"{title} {instruction} {task_summary}"
        if any(keyword in combined for keyword in ("准备", "工位", "断电", "安全")):
            return ["torso_link"]
        if any(keyword in combined for keyword in ("线缆", "接头", "连接")):
            return ["torso_link", self._default_focus_target(task_summary)]
        return [self._default_focus_target(task_summary)]
