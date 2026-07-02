# AI 管线端到端计时 Runbook (Task B4)

## 1. 启用计时中间件

计时中间件默认**关闭**。需在启动时设置环境变量 `PERF_TIMING=1`：

```bash
# 单次启动（不持久）
cd r-mos-backend
PERF_TIMING=1 python main.py

# 或配合 uvicorn
PERF_TIMING=1 uvicorn main:app --host 0.0.0.0 --port 8000
```

> **重要**：中间件在应用启动时注册，修改环境变量后需重启服务才生效。

未设置 `PERF_TIMING` 时，中间件完全不注册，响应头/日志行为与原版完全一致（零开销）。

---

## 2. 触发 AI/LLM 密集端点

以下端点涉及 LLM 调用或 AI 分析管线，是计时的主要观测目标：

| 端点 | 方法 | 描述 |
|------|------|------|
| `POST /api/v1/training/sessions` | POST | 创建训练会话（可含项目生成） |
| `POST /api/v1/training/sessions/{id}/submit` | POST | 提交训练（触发 AI 反馈生成） |
| `GET /api/v1/training/feedback/{id}` | GET | 获取 AI 生成的反馈 |
| `POST /api/v1/agent/workbench/draft` | POST | AI Workbench 草稿生成 |
| `POST /api/v1/agent/workbench/step` | POST | AI Workbench 步骤执行 |
| `POST /api/v1/robots/{id}/analysis` | POST | 机器人文档 AI 分析管线 |

### 示例：触发项目生成

```bash
# 需要 auth token，替换 YOUR_TOKEN
curl -s -X POST http://localhost:8000/api/v1/training/sessions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"robot_model_id": 1, "difficulty": "medium"}' \
  -D - | grep -i "x-process-time"
```

---

## 3. 读取计时数据

### 3a. 响应头（单次请求）

每个响应会携带 `X-Process-Time` 头（单位：毫秒，保留2位小数）：

```
X-Process-Time: 1843.27
```

用 `curl -D -` 或 Postman 查看响应头。

### 3b. 日志（批量/持续观测）

后端日志会输出结构化计时行（INFO 级）：

```
INFO     __main__:timing_middleware.py:46 TIMING route=/api/v1/training/sessions method=POST status=200 ms=1843.27
INFO     __main__:timing_middleware.py:46 TIMING route=/api/v1/agent/workbench/draft method=POST status=200 ms=3271.55
```

**提取日志中所有计时行：**

```bash
# 从 uvicorn/main.py 标准输出实时过滤
PERF_TIMING=1 python main.py 2>&1 | grep "^INFO.*TIMING"

# 或从文件（如有日志重定向）
grep "TIMING route=" logs/app.log | awk '{print $NF, $(NF-2)}'
```

---

## 4. 定位 LLM 调用耗时

`X-Process-Time` 反映的是 **服务端总处理时间**（含数据库查询 + LLM 调用 + 序列化）。

要进一步分离 LLM 调用耗时，有两种方式：

### 4a. 对比 LLM 服务本身的日志

LLM 调用通过 `app/services/llm/` 路由，相关日志关键词：
- `DeepSeek` / `MiniMax` 调用前后的 logger 输出
- `app/services/llm/router.py` 中的耗时 debug 日志

```bash
grep -E "llm|deepseek|minimax|LLM" logs/app.log -i | grep -v "^DEBUG"
```

### 4b. 差值估算

对同一端点：
- **纯 DB 操作端点**（如 GET /api/v1/sops）的 ms 值 ≈ DB + 序列化基线
- **AI 端点** ms 值 - 基线 ≈ LLM 调用时间估算

---

## 5. 记录基准数据

将测量结果记录到：
`docs/superpowers/plans/phase4-baseline.md` → **AI 管线** 章节

推荐格式：

```markdown
## AI 管线基准 (PERF_TIMING=1, 本地开发环境)

| 端点 | 方法 | P50 (ms) | P95 (ms) | 样本数 | 备注 |
|------|------|----------|----------|-------|------|
| /api/v1/training/sessions | POST | 1200 | 2800 | 10 | 含项目生成 |
| /api/v1/training/feedback/{id} | GET | 800 | 1500 | 10 | AI 反馈 |
| /api/v1/agent/workbench/draft | POST | 2500 | 4000 | 10 | LLM 草稿 |
```

---

## 6. 关闭计时（恢复默认）

不设置 `PERF_TIMING` 即可（或设为任意非 `"1"` 的值）：

```bash
# 正常启动（不含 PERF_TIMING）
python main.py
# 响应中无 X-Process-Time 头，无 TIMING 日志行
```

---

## 7. 实现细节

- **中间件文件**：`app/core/timing_middleware.py`（`TimingMiddleware` 继承 `BaseHTTPMiddleware`）
- **注册位置**：`main.py` 顶部中间件配置区块，`CORSMiddleware` 之前条件注册
- **计时精度**：使用 `time.perf_counter()`（纳秒级），输出毫秒保留2位小数
- **默认关闭保证**：`os.getenv("PERF_TIMING") == "1"` 精确匹配，未设置/其他值均不注册
