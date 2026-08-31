# 实时通道点修复复验

- 版本：0.1.0
- 日期：2026-08-30
- 分支：`audit/phase3-auth-control-realtime`
- 起始提交：`56751f5e959c60dac880f96db8b630ce73f8e75b`
- 结果提交：本文件所在提交
- 验证等级：E1 自动测试与静态链路；未启动服务，未执行多用户运行探针
- 总裁决：**CONDITIONAL**

## 1. 复核结论与修正

对提交 `56751f5e` 的独立复核确认：安全默认关闭方向正确，但原记录的 `PASS` 超出证据范围。

| 对象 | `56751f5e` 后状态 | 本轮结果 | 当前边界 |
|---|---|---|---|
| F-RT-01 心跳回执零调用 | 静态修复 | PASS（E1） | 新增真实端点接收循环测试；未做四心跳周期服务级验证 |
| F-RT-02 慢连接拖停 | PARTIAL | PASS（单元/异步测试范围） | 遥测、心跳、定向发送均增加单连接发送上限；慢连接清理后健康连接可继续多轮推送 |
| F-RT-03 定向参数失效 | 安全封堵 | PASS（防泄露）/ FAIL（功能可用） | 用户与频道过滤生效，但 M-03 未实现，真实连接仍无身份，因此教师监控三类消息继续安全不投递 |
| RT-GATE-05 时间格式 | 未复验 | PASS（生成格式的单元范围） | 心跳、遥测与教师事件不再生成 `+00:00Z` 双后缀；未做完整收发、拒绝非法输入或运行时格式门禁 |
| M-03 WebSocket 认证与隔离 | OPEN | OPEN | 本轮未增加认证、机器人归属或频道授权，不改变 P0 状态 |

## 2. 测试先行证据

### RED

命令：

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest \
  tests/unit/test_websocket_targeting.py tests/unit/test_teacher_monitor.py -q
```

实现前新增用例结果：`4 failed, 6 passed`。四个失败分别证明：

1. 永不返回的连接使定向发送超过测试上限；
2. 健康连接只收到第一批遥测，后续批次被拖停；
3. 串行心跳使健康连接收不到 ping；
4. 零投递时教师监控仍记录 `Published` / `Sent`。

### GREEN

同一命令实现后结果：`10 passed`，退出码 0。

扩展相关回归：

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest \
  tests/unit/test_websocket_targeting.py \
  tests/unit/test_teacher_monitor.py \
  tests/unit/test_telemetry_context_builder.py -q
```

结果：`22 passed`，退出码 0。警告均为既有 Pydantic V2 弃用警告，本轮未新增警告类别。

差异复核又发现心跳和遥测使用 `isoformat() + "Z"`，会生成 `+00:00Z` 双后缀。向既有遥测/心跳用例加入严格断言后，修复前结果为 `2 failed, 6 passed`；统一生成单一 `Z` 后缀。

独立代码复核随后指出三个遗漏：定向/遥测失败后只移表未关闭套接字、最后一条心跳连接可能在异步关闭中自取消、教师监控三类事件仍生成双 UTC 后缀。新增反例结果为 `4 failed, 7 passed`；修正关闭顺序、当前任务取消保护和教师事件时间后，目标测试 `11 passed`，扩展相关回归最终为 `22 passed`。

同一独立复核方第二轮确认上述三项均已关闭，未发现新的 Critical/Important；其只读环境独立复跑同样得到目标 `11 passed`、扩展 `22 passed`，且未修改文件。

## 3. 实现事实

- 遥测、心跳和教师监控定向发送均受单连接发送上限约束；超时或异常连接先执行有界关闭，再从连接表清理。
- 删除最后一条连接时不再取消正在执行清理的后台任务；关闭完成后循环自行停止，其他后台任务仍被取消。
- 心跳按连接并发发送，不再因字典中的第一条连接半开而阻断其余连接。
- 定向发送返回实际成功连接数；教师监控按返回值区分“已投递”和“未投递”，不再生成互相矛盾的成功日志。
- 回归测试通过 `_handle_websocket` 的真实接收循环发送前端使用的 `{"type":"pong"}`，验证状态被重置。
- 心跳、遥测和教师监控三类事件统一生成单一 UTC `Z` 后缀，不再输出 `+00:00Z`。

## 4. 不得外推的结论

- `22 passed` 不等于 RT-GATE 通过。
- 匿名连接、机器人隔离、用户身份、频道授权、四心跳周期、断线重连和完整时间格式收发/拒绝门禁仍未完成。
- 当前教师私信、步骤告警和班级事件在真实连接路径上仍为零投递；这是防泄露止血状态，不是功能恢复。
- 发送上限依赖底层 ASGI `send`/`close` 正常响应协程取消；本轮只验证了可取消的慢连接替身，未把“不响应取消的底层实现”写成已覆盖。
- 本轮不改变 A4、A6、M-03、E1、E2/E3/E4、`REL-BLOCK-01` 或 R1 的状态。

## 5. 工作区完整性

- 使用项目 `.env` 的后端回归共收集 976 项；其中 3 项需要连接本机 PostgreSQL 并写入随机临时行后清理。执行许可被拒绝后未绕过，因此这 3 项状态为 **NOT RUN / UNKNOWN**，不得写成 PASS 或 FAIL。
- 排除上述 3 项数据库门禁测试后，共收集 973 项，执行进度达到 100%，pytest 退出码 0：

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m dotenv \
  -f /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env run -- \
  /Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest -q \
  --disable-warnings \
  --ignore=tests/unit/test_audit_query_index_gate.py \
  --ignore=tests/unit/test_skill_registry_migration_gate.py
```

- 未加载 `.env` 的首次全量命令因生产模式密钥校验在收集阶段失败，属于环境输入错误，不计作代码回归结论；修正环境后只剩上述 3 项数据库连接受限。
- 测试改写了被 Git 跟踪的 `data/knowledge_store.json` 时间戳；复核差异后已恢复该测试副作用，未保留测试数据变化。
- 测试前后 `git status --short` 只包含本任务文件；未出现数据库、测试数据或既有跟踪数据的额外变化。
- `git diff --check` 通过。
- 未启动服务、未连接数据库、未执行迁移、未访问真实机器人或生产环境。
