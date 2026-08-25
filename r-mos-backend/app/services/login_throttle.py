"""登录失败限流（AUTH-105）。

Phase 1 记录：`/auth/login` 对错误密码只返回统一 401，不记失败次数、不限速、
不锁定，可对固定账号持续尝试。

设计取舍：
- 计数按 **(账号, 来源 IP)** 组合，避免单一维度带来的连带影响——只按账号会让
  攻击者用一个账号锁死真实用户；只按 IP 会让同一出口的整个校区互相牵连。
- **不做永久锁定**：永久锁定本身就是一种拒绝服务手段。窗口结束自动恢复。
- 锁定期内即使密码正确也拒绝，否则限流可被"撞对即通过"绕过。
- 成功登录清零该组合的计数。
- 状态存进程内：与 ADR-2026-08-21-runtime-topology 的**单进程单实例**决策一致，
  **不引入 Redis**。重启即清空——对暴力破解防护而言这是可接受的降级，
  因为重启会中断攻击者的连接与节奏。多副本部署一律视为配置错误（见该 ADR D1）。

时间由调用方传入（`now`），不在内部读时钟——这样测试可以直接推进时间，
不需要引入 freezegun 一类依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 阈值（2026-08-21 用户确认）
MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60
LOCKOUT_SECONDS = 15 * 60

ThrottleKey = tuple[str, str]


@dataclass
class LoginThrottle:
    """按 (账号, 来源) 组合的失败计数与临时锁定。"""

    max_failures: int = MAX_FAILURES
    window_seconds: int = WINDOW_SECONDS
    lockout_seconds: int = LOCKOUT_SECONDS
    _failures: dict[ThrottleKey, list[float]] = field(default_factory=dict)
    _locked_until: dict[ThrottleKey, float] = field(default_factory=dict)

    def locked_seconds_remaining(self, key: ThrottleKey, now: float) -> int:
        """仍处于锁定期则返回剩余秒数（>0），否则返回 0。"""
        until = self._locked_until.get(key)
        if until is None:
            return 0
        if now >= until:
            # 锁定自然到期：一并清掉计数，让用户回到干净状态
            self._locked_until.pop(key, None)
            self._failures.pop(key, None)
            return 0
        return int(until - now) + 1

    def record_failure(self, key: ThrottleKey, now: float) -> int:
        """记一次失败；达到阈值则开始锁定。返回锁定剩余秒数（未锁定为 0）。"""
        window_start = now - self.window_seconds
        recent = [ts for ts in self._failures.get(key, []) if ts > window_start]
        recent.append(now)
        self._failures[key] = recent

        if len(recent) >= self.max_failures:
            self._locked_until[key] = now + self.lockout_seconds
            return self.lockout_seconds
        return 0

    def reset(self, key: ThrottleKey) -> None:
        """登录成功后清零。"""
        self._failures.pop(key, None)
        self._locked_until.pop(key, None)

    def clear_all(self) -> None:
        """仅供测试隔离使用。"""
        self._failures.clear()
        self._locked_until.clear()


# 进程内单例（单进程部署约束下成立，见模块文档）
login_throttle = LoginThrottle()
