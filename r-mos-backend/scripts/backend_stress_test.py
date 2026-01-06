#!/usr/bin/env python3
"""
后端核心逻辑熔断测试（三明治测试法 - 第一层）

测试场景：
- 用户 A：正常流程 → 期望 100 分
- 用户 B：注入 E001 故障 → 期望分数 < 90
- 用户 C：跳过所有允许跳过的步骤 → 期望分数 < 100

运行方式：
    cd r-mos-backend
    source venv/bin/activate
    python scripts/backend_stress_test.py
"""
import asyncio
import aiohttp
import sys
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════════════════════

BASE_URL = "http://localhost:8000/api/v1"
SOP_ID = 1  # 使用第一个 SOP（假设已有种子数据）


class TestResult(Enum):
    PASSED = "✅ PASSED"
    FAILED = "❌ FAILED"
    ERROR = "⚠️ ERROR"


@dataclass
class UserScenario:
    name: str
    description: str
    inject_fault: Optional[str]  # E001_OVERHEAT 等
    skip_steps: bool  # 是否跳过可选步骤
    expected_score_min: int
    expected_score_max: int


# ═══════════════════════════════════════════════════════════════════════════════
# 测试场景定义
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIOS = [
    UserScenario(
        name="用户 A（正常流程）",
        description="完整执行所有步骤，无故障注入",
        inject_fault=None,
        skip_steps=False,
        expected_score_min=100,
        expected_score_max=100,
    ),
    UserScenario(
        name="用户 B（故障注入）",
        description="注入 E001_OVERHEAT 故障",
        inject_fault="E001_OVERHEAT",
        skip_steps=False,
        expected_score_min=0,
        expected_score_max=89,  # 期望分数 < 90
    ),
    UserScenario(
        name="用户 C（跳过步骤）",
        description="跳过所有允许跳过的步骤",
        inject_fault=None,
        skip_steps=True,
        expected_score_min=0,
        expected_score_max=99,  # 期望分数 < 100
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP 客户端
# ═══════════════════════════════════════════════════════════════════════════════

class APIClient:
    def __init__(self, session: aiohttp.ClientSession, user_name: str):
        self.session = session
        self.user_name = user_name

    async def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{BASE_URL}{path}"
        try:
            async with self.session.request(method, url, **kwargs) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    return {"error": True, "status": resp.status, "detail": text}
                return await resp.json()
        except Exception as e:
            return {"error": True, "status": 0, "detail": str(e)}

    async def get(self, path: str) -> Dict[str, Any]:
        return await self.request("GET", path)

    async def post(self, path: str, json: Dict = None) -> Dict[str, Any]:
        return await self.request("POST", path, json=json or {})


# ═══════════════════════════════════════════════════════════════════════════════
# 测试逻辑
# ═══════════════════════════════════════════════════════════════════════════════

async def run_scenario(scenario: UserScenario) -> Dict[str, Any]:
    """执行单个用户场景"""
    result = {
        "scenario": scenario.name,
        "description": scenario.description,
        "steps_executed": [],
        "timeline_events": [],
        "final_score": None,
        "task_status": None,
        "assertions": [],
        "result": TestResult.ERROR,
    }

    async with aiohttp.ClientSession() as session:
        client = APIClient(session, scenario.name)
        print(f"\n{'='*60}")
        print(f"🚀 {scenario.name}: {scenario.description}")
        print(f"{'='*60}")

        # ─────────────────────────────────────────────────────────────
        # Step 1: 创建任务
        # ─────────────────────────────────────────────────────────────
        print(f"[{scenario.name}] 创建任务...")
        task_resp = await client.post("/tasks", json={
            "title": f"熔断测试 - {scenario.name}",
            "sop_id": SOP_ID,
        })
        
        if task_resp.get("error"):
            print(f"[{scenario.name}] ❌ 创建任务失败: {task_resp}")
            result["assertions"].append(("创建任务", False, str(task_resp)))
            return result

        task_id = task_resp["id"]
        print(f"[{scenario.name}] ✅ 任务创建成功: ID={task_id}")
        result["assertions"].append(("创建任务", True, f"task_id={task_id}"))

        # ─────────────────────────────────────────────────────────────
        # Step 1.5: 启动任务（V2修复：pending -> in_progress）
        # ─────────────────────────────────────────────────────────────
        print(f"[{scenario.name}] 启动任务...")
        start_resp = await client.post(f"/tasks/{task_id}/start")
        if start_resp.get("error"):
            print(f"[{scenario.name}] ⚠️ 启动任务失败（可能已启动）: {start_resp.get('detail', '')[:100]}")
        else:
            print(f"[{scenario.name}] ✅ 任务已启动: status={start_resp.get('status')}")

        # ─────────────────────────────────────────────────────────────
        # Step 2: 获取 SOP 步骤数
        # ─────────────────────────────────────────────────────────────
        sop_resp = await client.get(f"/sops/{SOP_ID}")
        if sop_resp.get("error"):
            print(f"[{scenario.name}] ❌ 获取SOP失败: {sop_resp}")
            return result

        step_count = len(sop_resp.get("steps", []))
        steps = sop_resp.get("steps", [])
        print(f"[{scenario.name}] SOP 共 {step_count} 个步骤")

        # ─────────────────────────────────────────────────────────────
          # 故障注入（用户 B）
        # ─────────────────────────────────────────────────────────────
        if scenario.inject_fault:
            print(f"[{scenario.name}] 💉 注入故障: {scenario.inject_fault}")
            fault_resp = await client.post("/adapter/inject-fault", json={
                "fault_code": scenario.inject_fault,
                "target_part": "knee_right",  # V2 修正：joint_id -> target_part
            })
            if fault_resp.get("error"):
                print(f"[{scenario.name}] ⚠️ 故障注入失败（继续测试）: {fault_resp}")
            else:
                print(f"[{scenario.name}] ✅ 故障注入成功")

        # ─────────────────────────────────────────────────────────────
        # Step 4: 执行步骤
        # ─────────────────────────────────────────────────────────────
        for i, step in enumerate(steps, start=1):
            step_title = step.get("title", f"步骤{i}")
            is_skippable = step.get("is_skippable", False)

            # 用户 C 跳过可选步骤
            if scenario.skip_steps and is_skippable:
                print(f"[{scenario.name}] ⏭️ 跳过步骤 {i}: {step_title}")
                action = "skip"
            else:
                print(f"[{scenario.name}] ▶️ 执行步骤 {i}: {step_title}")
                action = "execute"

            step_resp = await client.post(f"/tasks/{task_id}/step", json={
                "step_index": i,
                "action": action,
                "parameters": {},
            })

            if step_resp.get("error"):
                print(f"[{scenario.name}] ❌ 步骤 {i} 失败: {step_resp}")
                result["steps_executed"].append({
                    "index": i,
                    "action": action,
                    "success": False,
                    "error": step_resp.get("detail"),
                })
                # 不中断，继续执行
            else:
                result["steps_executed"].append({
                    "index": i,
                    "action": action,
                    "success": True,
                    "status": step_resp.get("status"),
                    "message": step_resp.get("message"),
                })
                
                # 检查是否任务完成
                if step_resp.get("is_task_completed"):
                    print(f"[{scenario.name}] 🏁 任务完成标记已返回")
                    break

            # 小延迟，模拟真实操作
            await asyncio.sleep(0.05)

        # ─────────────────────────────────────────────────────────────
          # 清除故障（用户 B）- V2 修正：使用 DELETE 方法
        # ─────────────────────────────────────────────────────────────
        if scenario.inject_fault:
            await client.request("DELETE", f"/adapter/fault/{scenario.inject_fault}")
            print(f"[{scenario.name}] 🧹 故障已清除")

        # ─────────────────────────────────────────────────────────────
        # Step 6: 获取最终任务状态
        # ─────────────────────────────────────────────────────────────
        await asyncio.sleep(0.1)  # 等待数据库提交
        final_task = await client.get(f"/tasks/{task_id}")
        
        if final_task.get("error"):
            print(f"[{scenario.name}] ❌ 获取最终状态失败")
            return result

        result["final_score"] = final_task.get("final_score")
        result["task_status"] = final_task.get("status")

        print(f"[{scenario.name}] 最终状态: {final_task.get('status')}")
        print(f"[{scenario.name}] 最终得分: {result['final_score']}")

        # ─────────────────────────────────────────────────────────────
        # Step 7: 获取 Timeline 事件
        # ─────────────────────────────────────────────────────────────
        events_resp = await client.get(f"/tasks/{task_id}/events")
        if not events_resp.get("error") and isinstance(events_resp, list):
            result["timeline_events"] = [e.get("event_type") for e in events_resp]
            print(f"[{scenario.name}] Timeline: {result['timeline_events']}")

        # ─────────────────────────────────────────────────────────────
        # Step 8: 断言验证
        # ─────────────────────────────────────────────────────────────
        print(f"\n[{scenario.name}] 📊 断言验证:")

        # 断言 1: 任务状态
        status_ok = final_task.get("status") == "completed"
        result["assertions"].append((
            "任务状态 == completed",
            status_ok,
            f"实际: {final_task.get('status')}"
        ))
        print(f"  {'✅' if status_ok else '❌'} 任务状态: {final_task.get('status')}")

        # 断言 2: 分数范围
        score = result["final_score"]
        if score is not None:
            score_ok = scenario.expected_score_min <= score <= scenario.expected_score_max
            result["assertions"].append((
                f"分数 {scenario.expected_score_min} <= {score} <= {scenario.expected_score_max}",
                score_ok,
                f"实际分数: {score}"
            ))
            print(f"  {'✅' if score_ok else '❌'} 分数: {score} (期望: {scenario.expected_score_min}-{scenario.expected_score_max})")
        else:
            result["assertions"].append(("分数不为空", False, "分数为 None"))
            print(f"  ❌ 分数: None")

        # 断言 3: Timeline 事件顺序
        events = result["timeline_events"]
        expected_sequence = ["TASK_STARTED", "STEP_EXECUTED", "TASK_COMPLETED"]
        
        # ⚠️ 注意：事件类型名称可能与实际不同，需要根据后端实现调整
        # 这里检查是否存在关键事件
        has_start = any("START" in e.upper() for e in events) if events else False
        has_exec = any("EXECUTE" in e.upper() or "STEP" in e.upper() for e in events) if events else False
        has_complete = any("COMPLETE" in e.upper() for e in events) if events else False
        
        timeline_ok = has_start and has_exec and has_complete
        result["assertions"].append((
            "Timeline 包含: STARTED → EXECUTED → COMPLETED",
            timeline_ok,
            f"实际事件: {events}"
        ))
        print(f"  {'✅' if timeline_ok else '⚠️'} Timeline: {events[:5]}{'...' if len(events) > 5 else ''}")

        # 综合结果
        all_passed = all(a[1] for a in result["assertions"])
        result["result"] = TestResult.PASSED if all_passed else TestResult.FAILED

        return result


async def run_concurrent_test():
    """并发执行所有场景"""
    print("\n" + "═" * 70)
    print(" 🔥 后端核心逻辑熔断测试（并发模式）")
    print(" 三明治测试法 - 第一层")
    print("═" * 70)
    print(f"⏱️  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 测试场景: {len(SCENARIOS)} 个")
    print(f"🔗 API 地址: {BASE_URL}")

    # 预检查：确保后端在线
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/health") as resp:
                if resp.status != 200:
                    print("\n❌ 后端服务未启动！请先运行: python main.py")
                    return []
                health = await resp.json()
                print(f"✅ 后端健康: {health.get('status')} v{health.get('version')}")
        except Exception as e:
            print(f"\n❌ 无法连接后端: {e}")
            print("请确保后端服务正在运行: cd r-mos-backend && python main.py")
            return []

    # 并发执行所有场景
    print("\n🚀 启动并发测试（模拟 3 用户同时操作）...\n")
    
    results = await asyncio.gather(
        *[run_scenario(s) for s in SCENARIOS],
        return_exceptions=True
    )

    # 处理异常
    processed_results = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            processed_results.append({
                "scenario": SCENARIOS[i].name,
                "result": TestResult.ERROR,
                "error": str(r),
            })
        else:
            processed_results.append(r)

    return processed_results


def print_summary(results: List[Dict]):
    """打印测试汇总"""
    print("\n" + "═" * 70)
    print(" 📊 测试结果汇总")
    print("═" * 70)

    for r in results:
        status = r.get("result", TestResult.ERROR).value
        name = r.get("scenario", "Unknown")
        score = r.get("final_score", "N/A")
        print(f"{status} {name}")
        print(f"   └─ 最终得分: {score}")
        
        for assertion, passed, detail in r.get("assertions", []):
            icon = "✅" if passed else "❌"
            print(f"      {icon} {assertion}")

    # 统计
    passed = sum(1 for r in results if r.get("result") == TestResult.PASSED)
    failed = sum(1 for r in results if r.get("result") == TestResult.FAILED)
    errors = sum(1 for r in results if r.get("result") == TestResult.ERROR)

    print("\n" + "─" * 70)
    print(f"总计: {len(results)} 场景")
    print(f"  ✅ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    print(f"  ⚠️ 错误: {errors}")
    print("─" * 70)

    if failed == 0 and errors == 0:
        print("\n🎉 所有测试通过！后端核心逻辑熔断测试成功！")
        return 0
    else:
        print("\n⚠️ 存在失败或错误，请检查上述详情。")
        return 1


def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║     R-MOS 后端核心逻辑熔断测试                                    ║
    ║     三明治测试法 · 第一层                                         ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    results = asyncio.run(run_concurrent_test())
    if results:
        exit_code = print_summary(results)
        sys.exit(exit_code)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
