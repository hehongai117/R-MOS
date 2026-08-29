# 实时通道新发现（R0 期间由异源复核方发现）

- 版本：0.1.0｜日期：2026-08-29｜验证等级：**E1**（静态代码，未做运行时复现）
- 来源：R0 阶段 D-04 异源复核，Codex 对照 R-MOS 现状代码独立提出
- 主审复验：**三条全部成立**
- 状态：**A6 0.1.1 未覆盖**，需并入问题表

> **方法教训：** A6 对实时通道的审计集中在**认证与授权**（M-03），
> 没有审**存活与投递逻辑**。这三条都不是权限问题，因此整个审计序列没碰到。
> 安全审计的检查面不等于正确性审计的检查面。

## F-RT-01（P1，活的功能缺陷）：心跳必然误杀健康连接

**前后端都实现正确，中间少一行调用。**

| 环节 | 状态 |
|---|---|
| 前端回 pong | ✅ `r-mos-frontend/src/hooks/useWebSocket.ts:134` 发送 `JSON.stringify({type:'pong'})` |
| 后端识别 pong | ✅ `websocket_manager.py:91` 精确匹配 `'{"type":"pong"}'`，重置 `last_pong` 与 `missed_pongs` |
| **调用该处理函数** | ❌ **`handle_message` 全仓零调用者** |
| 端点侧 | `websocket.py:30` `data = await websocket.receive_text()` 后仅 `logger.debug`，注释写「MVP阶段不处理客户端消息，仅接收」 |

**后果推演**（`HEARTBEAT_INTERVAL=30`、`MAX_MISSED_PONGS=3`）：

`last_pong` 只在连接建立时由 `field(default_factory=...)` 赋值，此后**永不更新** →

| 时刻 | `now - last_pong` | 判定 |
|---|---|---|
| t=30s | 30s | 未超 60s |
| t=60s | 60s | 未超（严格大于） |
| t=90s | 90s | **missed_pongs=1** |
| t=120s | 120s | missed_pongs=2 |
| t=150s | 150s | **missed_pongs=3 = MAX → 强制关闭，reason="Heartbeat timeout"** |

**每条 WebSocket 连接在约 150 秒后被强制断开，与客户端是否健康无关。**
这直接影响 5Hz 遥测（`WS /ws/robot/status`）这一招牌功能。

**修复**：在 `websocket.py` 的接收循环中调用 `manager.handle_message(websocket, data)`。
`handle_message` 本身实现正确，无需改动。

> **为什么审计没发现**：静态权限扫描看的是「有没有认证依赖」，
> 看不见「有处理函数但没人调用」。这与 A6 M-16「定义先行、实现未跟上」同类，
> 但表现在**运行时行为**而非数据表。

## F-RT-02（P1）：广播串行，单个慢连接拖垮全体

`send_to_user`、`broadcast_to_channel` 等均为：

```python
for conn_id, state in list(self.connections.items()):
    await state.websocket.send_json(message)   # 串行 await
```

一个慢速或半开连接会**阻塞后续所有连接的本轮推送**。在 5Hz 推送下，
单个坏连接即可让全体客户端的实时性劣化。

**修复方向**：`asyncio.gather(..., return_exceptions=True)` 并发投递，或按连接维护独立发送队列。

## F-RT-03（P1）：`broadcast_to_channel` 是第三个「名不副实」的广播函数

`websocket_manager.py:195-207`：

```python
async def broadcast_to_channel(self, channel: str, message: dict) -> None:
    # 目前简化为向所有连接广播
    # 实际实现应该维护 channel -> connections 映射
    for conn_id, state in list(self.connections.items()):
        await state.websocket.send_json(message)
```

**`channel` 参数完全不被使用。** A6 的 M-03 只列了 `send_to_user`，
**漏了这一个同类实现**——即「按频道广播」同样是全量广播。

因此 M-03「`send_to_user` 实为全量广播」应扩为：
**连接管理器不存在任何维度的收敛，`user` 与 `channel` 两个参数都是装饰性的。**

## 与 M-19 的关系

Codex 另指出「连接表只在本进程内」——该点 A6 已由 M-19 覆盖
（`manager` 为 8 个持可变状态单例之一），此处不重复登记，
但可作为 M-19 后果的具体实例：**跨实例部署时，一个实例推送的遥测其他实例的客户端收不到。**

## 处置建议

| 编号 | 严重度 | 建议 |
|---|---|---|
| F-RT-01 | **P1** | 归入改造首批。一行调用即可修复，但影响招牌功能 |
| F-RT-02 | P1 | 与 M-03 的 WS 改造一并处理 |
| F-RT-03 | P1 | **并入 M-03**，修正其受影响实例描述 |

三条均**不需要等待任何决策**，与 M-04/M-05/M-10 同属独立点修。
