# 测试计划

## 全量清单（页面/按钮/权限）

### 页面清单（按角色与入口）
说明：当前前端未见显式鉴权/角色路由，以下按业务预期分配；权限不足状态用于后端鉴权接入后验证。

| 角色 | 路由 | 页面 | 入口 | 页面状态 |
| --- | --- | --- | --- | --- |
| 教师/学生 | `/` | 首页 | 侧边栏“首页” | 加载中/统计展示/空态(统计为0)/异常占位 |
| 教师/学生 | `/sops` | SOP 列表 | 侧边栏“SOP列表”、首页快捷入口、任务/报告返回 | 列表加载/空态/异常提示 |
| 教师/学生 | `/tasks/:taskId` | 任务执行 | SOP 列表“开始训练” | 加载中/任务不存在/进行中/暂停 |
| 教师/学生 | `/reports/:taskId` | 任务报告 | 任务完成弹窗、直接访问 | 加载中/错误结果页/正常报告 |
| 教师/学生 | `/reports` | 任务报告(缺少 taskId) | 旧侧边栏或手动输入 | 异常：taskId 缺失导致页面停留在加载态 |
| 教师/管理员 | `/monitor` | 实时监控 | 侧边栏“实时监控”、首页快捷入口 | 连接中/已连接/数据过期/断开告警 |
| 教师/管理员 | `/incidents` | 事件列表 | 侧边栏“事件列表” | 列表加载/使用 mock 数据/异常提示 |
| 教师/管理员 | `/evidence` | 证据包 | 侧边栏“证据包” | 列表加载/详情抽屉/使用 mock 数据 |
| 教师/管理员 | `/assessments` | 评估状态 | 侧边栏“评估状态” | 列表加载/使用 mock 数据/异常提示 |
| 教师/管理员 | `/atom01` | 机器人演示 | 侧边栏“机器人演示” | 3D 载入/控制可用/异常占位 |
| 教师/管理员 | `/maintenance` | SOP 维保系统 | 侧边栏“SOP 维保系统” | 3D 载入/模式切换/部件选中/异常占位 |
| 学生/教师 | `/teaching/assignments` | 教学作业中心 | 侧边栏“教学中心” | 作业列表加载/空态/异常提示/双角色 Tab |
| 学生/教师 | `/teaching/attempts/:id` | 教学尝试 | 作业中心“开始/进入尝试” | 加载中/不存在/步骤执行/证据生成 |
| 学生/教师 | `/teaching/attempts/:id/evidence` | 教学证据摘要 | 尝试页“查看证据摘要”、作业中心“查看证据” | 加载中/不存在/摘要为空/摘要展示 |
| 教师 | `/teaching/attempts/:id/diagnosis` | 教学诊断报告 | 证据摘要“查看诊断报告” | 加载中/不存在/诊断展示/空列表 |
| 管理员 | `/admin/faults` | 故障案例库管理 | 侧边栏“故障管理”、首页快捷入口 | 列表加载/空态/详情抽屉/新建编辑弹窗 |
| 管理员 | `/admin/seed-data` | 种子数据导入说明 | 侧边栏“种子数据” | 说明页渲染/无交互/异常占位 |
| 管理员 | `/admin/settings` | 系统设置(未实现) | `Sidebar.tsx` 菜单 | 路由缺失/白屏/404 |

### 按钮清单（全按钮覆盖）
#### 全局导航（`AppLayout.tsx` 侧边栏）
- 首页：正常路径=跳转 `/`；异常路径=路由缺失显示空白；权限路径=无权限隐藏或禁用菜单。
- SOP列表：正常路径=跳转 `/sops`；异常路径=路由缺失显示空白；权限路径=无权限隐藏或禁用菜单。
- SOP 维保系统：正常路径=跳转 `/maintenance`；异常路径=路由缺失显示空白；权限路径=无权限隐藏或禁用菜单。
- 机器人演示：正常路径=跳转 `/atom01`；异常路径=路由缺失显示空白；权限路径=无权限隐藏或禁用菜单。
- 教学中心：正常路径=跳转 `/teaching/assignments`；异常路径=路由缺失显示空白；权限路径=无权限隐藏或禁用菜单。
- 实时监控：正常路径=跳转 `/monitor`；异常路径=路由缺失显示空白；权限路径=无权限隐藏或禁用菜单。
- 事件列表：正常路径=跳转 `/incidents`；异常路径=路由缺失显示空白；权限路径=无权限隐藏或禁用菜单。
- 证据包：正常路径=跳转 `/evidence`；异常路径=路由缺失显示空白；权限路径=无权限隐藏或禁用菜单。
- 评估状态：正常路径=跳转 `/assessments`；异常路径=路由缺失显示空白；权限路径=无权限隐藏或禁用菜单。
- 故障管理：正常路径=跳转 `/admin/faults`；异常路径=路由缺失显示空白；权限路径=非管理员隐藏或禁用菜单。
- 种子数据：正常路径=跳转 `/admin/seed-data`；异常路径=路由缺失显示空白；权限路径=非管理员隐藏或禁用菜单。

#### `/` 首页
- 快捷入口卡片（SOP/监控/故障）：正常路径=点击卡片跳转对应路由；异常路径=路由缺失或跳转失败；权限路径=无权限时卡片隐藏或禁用。
- “进入”链接按钮：正常路径=跳转对应路由；异常路径=跳转失败无响应；权限路径=无权限时禁用或不展示。
- “查看全部”按钮：正常路径=跳转 `/sops`；异常路径=跳转失败；权限路径=无权限时禁用或不展示。

#### `/sops` SOP 列表
- 创建SOP：正常路径=进入创建流程(当前未实现，预期弹窗/跳转)；异常路径=点击无响应或提示错误；权限路径=非教师/管理员不可见或禁用。
- 开始训练：正常路径=调用创建任务成功后跳转 `/tasks/:taskId`；异常路径=接口失败提示“创建任务失败”；权限路径=无权创建任务返回 403 并提示。
- 分页切换：正常路径=翻页刷新列表；异常路径=列表加载失败提示“加载SOP列表失败”；权限路径=无权访问列表返回 403。

#### `/tasks/:taskId` 任务执行
- 执行下一步：正常路径=执行成功并刷新状态或弹出完成提示；异常路径=接口失败提示“步骤执行失败”；权限路径=无权执行步骤返回 403。
- 暂停：正常路径=状态变为 paused；异常路径=接口失败提示“暂停失败”；权限路径=无权暂停返回 403。
- 继续执行：正常路径=状态恢复 in_progress；异常路径=接口失败提示“恢复失败”；权限路径=无权恢复返回 403。
- 返回SOP列表：正常路径=跳转 `/sops`；异常路径=跳转失败；权限路径=无权限时禁用或重定向。

#### `/reports/:taskId` 任务报告
- 返回SOP列表：正常路径=跳转 `/sops`；异常路径=跳转失败；权限路径=无权限时禁用或重定向。

#### `/monitor` 实时监控
- 点击重连：正常路径=触发 WebSocket 重连并恢复数据；异常路径=重连失败仍提示断开；权限路径=无权查看监控返回 403 或隐藏入口。

#### `/incidents` 事件列表
- 分页切换：正常路径=翻页刷新列表；异常路径=后端失败回落 mock 并提示；权限路径=无权查看返回 403。

#### `/evidence` 证据包
- 查看：正常路径=打开详情抽屉并展示条目；异常路径=接口失败提示“无法加载证据详情”或 fallback mock；权限路径=无权查看返回 403。
- 抽屉关闭：正常路径=关闭详情抽屉；异常路径=抽屉无法关闭；权限路径=无影响。
- 分页切换：正常路径=翻页刷新列表；异常路径=后端失败回落 mock；权限路径=无权查看返回 403。

#### `/assessments` 评估状态
- 分页切换：正常路径=翻页刷新列表；异常路径=后端失败回落 mock 并提示；权限路径=无权查看返回 403。

#### `/teaching/assignments` 教学作业中心
- 学生入口“开始”：正常路径=创建尝试并跳转 `/teaching/attempts/:id`；异常路径=提示“请输入有效的学生编号”或接口失败提示；权限路径=无权开始作业返回 403。
- 学生入口“刷新”：正常路径=重新加载作业列表；异常路径=接口失败提示；权限路径=无权查看返回 403。
- 教师视图“查看提交”：正常路径=打开提交抽屉并展示列表；异常路径=接口失败提示“加载尝试列表失败”；权限路径=无权查看返回 403。
- 尝试列表“进入尝试”：正常路径=跳转 `/teaching/attempts/:id`；异常路径=跳转失败；权限路径=无权查看返回 403。
- 尝试列表“查看证据”：正常路径=跳转 `/teaching/attempts/:id/evidence`；异常路径=跳转失败或 404；权限路径=无权查看返回 403。

#### `/teaching/attempts/:id` 教学尝试
- 启动任务：正常路径=任务状态进入 in_progress；异常路径=提示“启动任务失败”；权限路径=无权操作返回 403。
- 执行下一步：正常路径=步骤执行成功，完成时写入证据并提示；异常路径=提示“步骤执行失败/证据生成失败”；权限路径=无权执行返回 403。
- 查看证据摘要：正常路径=跳转 `/teaching/attempts/:id/evidence`；异常路径=证据未生成返回 404；权限路径=无权查看返回 403。
- 返回作业列表：正常路径=跳转 `/teaching/assignments`；异常路径=跳转失败；权限路径=无权访问返回 403。

#### `/teaching/attempts/:id/evidence` 教学证据摘要
- 查看诊断报告：正常路径=跳转 `/teaching/attempts/:id/diagnosis`；异常路径=诊断不存在提示；权限路径=无权查看返回 403。
- 返回尝试页面：正常路径=跳转 `/teaching/attempts/:id`；异常路径=跳转失败；权限路径=无权访问返回 403。
- 返回作业列表：正常路径=跳转 `/teaching/assignments`；异常路径=跳转失败；权限路径=无权访问返回 403。

#### `/teaching/attempts/:id/diagnosis` 教学诊断报告
- 返回证据摘要：正常路径=跳转 `/teaching/attempts/:id/evidence`；异常路径=跳转失败；权限路径=无权查看返回 403。
- 返回尝试页面：正常路径=跳转 `/teaching/attempts/:id`；异常路径=跳转失败；权限路径=无权查看返回 403。
- 返回作业列表：正常路径=跳转 `/teaching/assignments`；异常路径=跳转失败；权限路径=无权访问返回 403。

#### `/atom01` 机器人演示
- 播放/暂停动画：正常路径=开始/暂停行走动画；异常路径=动画状态不更新；权限路径=无权限时禁用控制。
- 重置姿态：正常路径=关节角度归零；异常路径=关节状态不重置；权限路径=无权限时禁用控制。
- 预设姿态：正常路径=应用站立/行走/下蹲/举手；异常路径=姿态不生效；权限路径=无权限时禁用控制。
- 关节组切换：正常路径=切换分组展示；异常路径=分组切换失败；权限路径=无权限时禁用控制。
- 关节故障开关：正常路径=故障标记切换；异常路径=状态不更新；权限路径=无权限时禁用控制。

#### `/maintenance` SOP 维保系统
- 视图模式切换：正常路径=正常/爆炸图/透视切换；异常路径=切换无响应；权限路径=无权限时禁用切换。
- 模式选择(教学/考试/维保)：正常路径=弹窗确认并切换模式；异常路径=确认后未切换；权限路径=无权限时禁用选择。
- 爆炸图控制按钮(收起/30%/60%/完全展开)：正常路径=爆炸程度更新；异常路径=视图无变化；权限路径=无权限时禁用控制。
- 拆卸动画播放：正常路径=播放/停止拆卸动画；异常路径=播放状态异常；权限路径=无权限时禁用控制。
- 零件选择/取消选中：正常路径=显示零件详情/取消选中；异常路径=详情不更新；权限路径=无权限时禁用操作。
- 螺丝/工具选择：正常路径=工具/螺丝状态联动；异常路径=选择无效；权限路径=无权限时禁用选择。
- SOP 播放器控件：正常路径=脚本播放并驱动步骤；异常路径=播放失败提示；权限路径=无权限时禁用播放。
- 考试结束“重置”：正常路径=重置评分与进度；异常路径=重置无效；权限路径=无权限时禁用。

#### `/admin/faults` 故障案例库管理
- 刷新：正常路径=重新加载列表；异常路径=提示“加载故障案例失败”；权限路径=非管理员禁用或隐藏。
- 添加故障案例：正常路径=打开新建弹窗；异常路径=弹窗无法打开；权限路径=非管理员禁用或隐藏。
- 查看详情：正常路径=打开详情抽屉；异常路径=提示“获取详情失败”；权限路径=非管理员禁用或隐藏。
- 编辑：正常路径=打开编辑弹窗并回填；异常路径=回填失败；权限路径=非管理员禁用或隐藏。
- 删除：正常路径=确认后删除并刷新；异常路径=提示“删除失败”；权限路径=非管理员禁用或隐藏。
- 表单提交：正常路径=创建/更新成功并提示；异常路径=提示“创建失败/更新失败”；权限路径=非管理员禁用或隐藏。
- 表单取消：正常路径=关闭弹窗；异常路径=弹窗无法关闭；权限路径=无影响。

#### `/admin/seed-data` 种子数据导入说明
- 无显式按钮：正常路径=页面静态内容可见；异常路径=渲染失败；权限路径=非管理员禁用或隐藏入口。

### 权限矩阵与角色覆盖
说明：矩阵为预期角色划分，待后端鉴权接入后执行 401/403 或重定向验证。

| 页面/按钮 | 学生 | 教师 | 管理员 | 备注 |
| --- | --- | --- | --- | --- |
| `/` 首页 | 可见/可用 | 可见/可用 | 可见/可用 | 入口统一 |
| `/sops` SOP 列表 | 可见/可用 | 可见/可用 | 可见/可用 | 训练入口 |
| `/tasks/:taskId` 任务执行 | 可见/可用 | 可见/可用 | 可见/可用 | 训练执行 |
| `/reports/:taskId` 任务报告 | 可见/可用 | 可见/可用 | 可见/可用 | 训练结果 |
| `/monitor` 实时监控 | 可见/可用 | 可见/可用 | 可见/可用 | 运维监控 |
| `/incidents` 事件列表 | 可见/可用 | 可见/可用 | 可见/可用 | 运维记录 |
| `/evidence` 证据包 | 可见/可用 | 可见/可用 | 可见/可用 | 审计凭证 |
| `/assessments` 评估状态 | 可见/可用 | 可见/可用 | 可见/可用 | 外部评估 |
| `/atom01` 机器人演示 | 可见/可用 | 可见/可用 | 可见/可用 | 演示训练 |
| `/maintenance` SOP 维保系统 | 可见/可用 | 可见/可用 | 可见/可用 | 维保训练 |
| `/teaching/assignments` 学生入口 | 可见/可用 | 可见/可用 | 可见/可用 | 角色通过 Tab 区分 |
| `/teaching/assignments` 教师视图 | 可见/可用 | 可见/可用 | 可见/可用 | 角色通过 Tab 区分 |
| `/teaching/attempts/:id` 教学尝试 | 可见/可用 | 可见/可用 | 可见/可用 | 过程执行 |
| `/teaching/attempts/:id/evidence` 证据摘要 | 可见/可用 | 可见/可用 | 可见/可用 | 证据回放 |
| `/teaching/attempts/:id/diagnosis` 诊断报告 | 不可用 | 可见/可用 | 可见/可用 | 仅教师/管理可看 |
| `/admin/faults` 故障案例管理 | 不可用 | 不可用 | 可见/可用 | 管理员专用 |
| `/admin/seed-data` 种子数据说明 | 不可用 | 不可用 | 可见/可用 | 管理员专用 |
| 故障案例 CRUD | 不可用 | 不可用 | 可见/可用 | 管理员专用 |

越权与边界用例（对应不可用项）
- 学生访问 `/admin/faults`：预期 403 或重定向到 `/` 并隐藏管理菜单。
- 学生访问 `/admin/seed-data`：预期 403 或重定向到 `/` 并隐藏管理菜单。
- 教师访问 `/admin/faults`：预期 403 或重定向到 `/` 并隐藏管理菜单。
- 教师访问 `/admin/seed-data`：预期 403 或重定向到 `/` 并隐藏管理菜单。
- 学生访问 `/teaching/attempts/:id/diagnosis`：预期 403 或不展示“查看诊断报告”按钮，直达 URL 被拦截。

## 任务4：后端 API 清单与按钮交叉引用

### Endpoint 文件覆盖（12）
| 文件 | 主要路径 |
| --- | --- |
| `r-mos-backend/app/api/v1/endpoints/health.py` | `/api/v1/health` |
| `r-mos-backend/app/api/v1/endpoints/adapter.py` | `/api/v1/adapter/*` |
| `r-mos-backend/app/api/v1/endpoints/websocket.py` | `/ws/robot/status` |
| `r-mos-backend/app/api/v1/endpoints/tasks.py` | `/api/v1/tasks/*` |
| `r-mos-backend/app/api/v1/endpoints/sops.py` | `/api/v1/sops/*` |
| `r-mos-backend/app/api/v1/endpoints/fault_cases.py` | `/api/v1/fault-cases/*` |
| `r-mos-backend/app/api/v1/endpoints/incidents.py` | `/api/v1/incidents/*` |
| `r-mos-backend/app/api/v1/endpoints/observations.py` | `/api/v1/observations/*` |
| `r-mos-backend/app/api/v1/endpoints/evidence.py` | `/api/v1/evidence-bundles/*` |
| `r-mos-backend/app/api/v1/endpoints/assessments.py` | `/api/v1/assessments/*`、`/api/v1/assessment-providers/*` |
| `r-mos-backend/app/api/v1/endpoints/teaching.py` | `/api/v1/*`（教学域） |
| `r-mos-backend/main.py` | `/` |

### API 回归测试用例（含按钮映射）
- 用例编号：API-01
  - 关联文件：`r-mos-backend/main.py`
  - 方法/路径：`GET /`
  - 关联页面/按钮：系统可用性探针
  - 期望结果：`200`，返回 service/version/status/health
  - 标签：P2
- 用例编号：API-02
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/health.py`
  - 方法/路径：`GET /api/v1/health`
  - 关联页面/按钮：系统可用性探针
  - 期望结果：`200`，返回状态与依赖检查结果
  - 标签：P1
- 用例编号：API-03
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/sops.py`
  - 方法/路径：`GET /api/v1/sops`
  - 关联页面/按钮：`/sops` SOP 列表加载
  - 期望结果：`200`，返回 SOP 列表
  - 标签：P0
- 用例编号：API-04
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/tasks.py`
  - 方法/路径：`POST /api/v1/tasks`
  - 关联页面/按钮：`/sops` → “开始训练”
  - 期望结果：`201`，返回 task_id
  - 标签：P0
- 用例编号：API-05
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/tasks.py`
  - 方法/路径：`GET /api/v1/tasks/{task_id}`
  - 关联页面/按钮：`/tasks/:taskId` 加载
  - 期望结果：`200`，返回任务详情
  - 标签：P0
- 用例编号：API-06
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/tasks.py`
  - 方法/路径：`POST /api/v1/tasks/{task_id}/step`
  - 关联页面/按钮：`/tasks/:taskId` → “执行下一步”
  - 期望结果：`200`，返回步骤执行结果
  - 标签：P0
- 用例编号：API-07
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/tasks.py`
  - 方法/路径：`GET /api/v1/tasks/{task_id}/report`
  - 关联页面/按钮：`/reports/:taskId` 报告加载
  - 期望结果：`200`，返回评分与步骤明细
  - 标签：P0
- 用例编号：API-08
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/teaching.py`
  - 方法/路径：`GET /api/v1/assignments`
  - 关联页面/按钮：`/teaching/assignments` 列表加载
  - 期望结果：`200`，返回作业列表
  - 标签：P0
- 用例编号：API-09
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/teaching.py`
  - 方法/路径：`POST /api/v1/assignments/{assignment_id}/attempts`
  - 关联页面/按钮：`/teaching/assignments` → “开始”
  - 期望结果：`201`，返回 attempt_id
  - 标签：P0
- 用例编号：API-10
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/teaching.py`
  - 方法/路径：`GET /api/v1/assignments/{assignment_id}/attempts`
  - 关联页面/按钮：`/teaching/assignments` → “查看提交”
  - 期望结果：`200`，返回尝试列表
  - 标签：P1
- 用例编号：API-11
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/teaching.py`
  - 方法/路径：`GET /api/v1/attempts/{attempt_id}/evidence`
  - 关联页面/按钮：`/teaching/attempts/:id/evidence` 加载
  - 期望结果：`200`，返回证据摘要
  - 标签：P0
- 用例编号：API-12
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/teaching.py`
  - 方法/路径：`GET /api/v1/attempts/{attempt_id}/diagnosis`
  - 关联页面/按钮：`/teaching/attempts/:id/diagnosis` 加载
  - 期望结果：`200`，返回诊断报告
  - 标签：P0
- 用例编号：API-13
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/fault_cases.py`
  - 方法/路径：`GET /api/v1/fault-cases`
  - 关联页面/按钮：`/admin/faults` 列表加载
  - 期望结果：`200`，返回故障案例列表
  - 标签：P1
- 用例编号：API-14
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/fault_cases.py`
  - 方法/路径：`POST /api/v1/fault-cases`
  - 关联页面/按钮：`/admin/faults` → “添加故障案例”
  - 期望结果：`201`，新建成功
  - 标签：P1
- 用例编号：API-15
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/incidents.py`
  - 方法/路径：`GET /api/v1/incidents`
  - 关联页面/按钮：`/incidents` 列表加载
  - 期望结果：`200`，返回事件列表
  - 标签：P1
- 用例编号：API-16
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/evidence.py`
  - 方法/路径：`GET /api/v1/evidence-bundles`
  - 关联页面/按钮：`/evidence` 列表加载
  - 期望结果：`200`，返回证据包列表
  - 标签：P1
- 用例编号：API-17
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/assessments.py`
  - 方法/路径：`GET /api/v1/assessments`
  - 关联页面/按钮：`/assessments` 列表加载
  - 期望结果：`200`，返回评估列表
  - 标签：P1
- 用例编号：API-18
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/observations.py`
  - 方法/路径：`GET /api/v1/observations`
  - 关联页面/按钮：接口直测
  - 期望结果：`200`，返回观测数据列表
  - 标签：P2
- 用例编号：API-19
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/adapter.py`
  - 方法/路径：`GET /api/v1/adapter/info`
  - 关联页面/按钮：监控基础信息校验
  - 期望结果：`200`，返回机器人信息
  - 标签：P2
- 用例编号：API-20
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/adapter.py`
  - 方法/路径：`POST /api/v1/adapter/inject-fault`
  - 关联页面/按钮：监控故障注入直测
  - 期望结果：`200`，返回注入结果
  - 标签：P2

### `WebSocket` 连接测试用例
- 用例编号：WS-01
  - 关联文件：`r-mos-backend/app/api/v1/endpoints/websocket.py`
  - 路径：`/ws/robot/status`
  - 关联页面/按钮：`/monitor` 页面加载即连接
  - 期望结果：连接成功，状态为 connected，收到 telemetry
  - 标签：P0
- 用例编号：WS-02
  - 关联文件：`r-mos-frontend/src/hooks/useWebSocket.ts`
  - 场景：收到 `type=ping` 时客户端返回 `pong`
  - 关联页面/按钮：`/monitor` 心跳处理
  - 期望结果：客户端发送 `pong`，连接不中断
  - 标签：P1
- 用例编号：WS-03
  - 关联文件：`r-mos-frontend/src/hooks/useWebSocket.ts`
  - 场景：服务端断开后指数退避重连
  - 关联页面/按钮：`/monitor` → “点击重连”
  - 期望结果：自动重连至上限，达到上限进入 failed
  - 标签：P1
- 用例编号：WS-04
  - 关联文件：`r-mos-frontend/src/hooks/useWebSocket.ts`
  - 场景：`5s` 无 telemetry 触发 stale
  - 关联页面/按钮：`/monitor` 状态提示
  - 期望结果：`isDataStale=true`，显示“数据已过期”
  - 标签：P1

## 任务5：风险分级（P0/P1/P2）

### 分级原则
- P0：核心闭环（创建任务、执行步骤、证据/诊断、评分报告）
- P1：高频关键页与管理操作（列表/编辑/监控稳定性）
- P2：低频或运维直测（适配器/观测等）

### 分级汇总（按用例编号）
- P0：API-03、API-04、API-05、API-06、API-07、API-08、API-09、API-11、API-12、WS-01
- P1：API-02、API-10、API-13、API-14、API-15、API-16、API-17、WS-02、WS-03、WS-04
- P2：API-01、API-18、API-19、API-20

## 阶段一回归矩阵（任务1-任务6）

> 说明：所有用例优先使用 `python r-mos-backend/scripts/seed_teaching_demo.py --reset` 生成教学演示数据。  
> 说明：需要 `assignment_id`、`class_id` 的场景，以脚本输出为准。  
> 说明：需要 `attempt_id` 的场景，先执行以下命令创建尝试并记录返回的 `id`：  
> `curl -X POST http://localhost:8000/api/v1/assignments/{assignment_id}/attempts -H "Content-Type: application/json" -d '{"studentId": {student_id}}'`

### 任务1（数据模型与迁移）

- 用例编号：T1-01
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments/{assignment_id}
    ```
  - 可选界面：`/teaching/assignments`
  - 期望结果（关键字段+状态码）：
    - `200`，包含 `id`、`classId`、`title`、`sopId`
  - 标签：P0

- 用例编号：T1-02
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/classes/{class_id}
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，`metadata` 为对象
  - 标签：P1

### 任务2（数据结构与字段输出）

- 用例编号：T2-01
  - 角色：学生
  - 前置数据/种子命令：无
  - 接口验收（curl）：
    ```bash
    curl -X POST http://localhost:8000/api/v1/guidance-policies \
      -H "Content-Type: application/json" \
      -d '{"name": "练习模式", "baseMode": "teaching"}'
    ```
  - 期望结果（关键字段+状态码）：
    - `201`，包含 `baseMode`、`allowGhostHand`、`allowHintButton`、`showErrorDetails`、`maxRetryCount`
  - 标签：P0

- 用例编号：T2-02
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，包含 `diagnosisCode`、`pathScore`、`evidenceQualityScore`（允许为空）
  - 标签：P1

### 任务3（教学服务层与状态流转）

- 用例编号：T3-01
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X POST http://localhost:8000/api/v1/assignments/{assignment_id}/attempts \
      -H "Content-Type: application/json" \
      -d '{"studentId": {student_id}}'
    curl -X POST http://localhost:8000/api/v1/assignments/{assignment_id}/attempts \
      -H "Content-Type: application/json" \
      -d '{"studentId": {student_id}}'
    ```
  - 期望结果（关键字段+状态码）：
    - 两次均 `201`，第二次 `attemptIndex = 第一次 + 1`
  - 标签：P0

- 用例编号：T3-02
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X PATCH http://localhost:8000/api/v1/attempts/{attempt_id} \
      -H "Content-Type: application/json" \
      -d '{"status": "completed"}'
    curl -X POST http://localhost:8000/api/v1/attempts/{attempt_id}/grade \
      -H "Content-Type: application/json" \
      -d '{"score": 95}'
    ```
  - 期望结果（关键字段+状态码）：
    - 第一步 `200`，`status = completed`
    - 第二步 `200`，`status = graded`，`score` 有值
  - 标签：P0

- 用例编号：T3-03
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X PATCH http://localhost:8000/api/v1/attempts/{attempt_id} \
      -H "Content-Type: application/json" \
      -d '{"status": "graded"}'
    curl -X PATCH http://localhost:8000/api/v1/attempts/{attempt_id} \
      -H "Content-Type: application/json" \
      -d '{"status": "completed"}'
    ```
  - 期望结果（关键字段+状态码）：
    - 第二步 `409`，错误码 `INVALID_ATTEMPT_STATUS_TRANSITION`
  - 标签：P1

### 任务4（教学接口与错误处理）

- 用例编号：T4-01
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，返回数组，元素包含 `id`、`classId`、`title`
  - 标签：P0

- 用例编号：T4-02
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X POST http://localhost:8000/api/v1/enrollments \
      -H "Content-Type: application/json" \
      -d '{"classId": {class_id}, "studentId": {student_id}}'
    curl -X POST http://localhost:8000/api/v1/enrollments \
      -H "Content-Type: application/json" \
      -d '{"classId": {class_id}, "studentId": {student_id}}'
    ```
  - 期望结果（关键字段+状态码）：
    - 第二次 `409`，错误码 `ALREADY_ENROLLED`
  - 标签：P0

- 用例编号：T4-03
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments/{assignment_id}/attempts
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，元素包含 `attemptIndex`、`status`
  - 标签：P1

### 任务5（证据引擎与证据关联）

- 用例编号：T5-01
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/start
    curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/step \
      -H "Content-Type: application/json" \
      -d '{"step_index": 1, "action": "inspect"}'
    curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/step \
      -H "Content-Type: application/json" \
      -d '{"step_index": 2, "action": "execute"}'
    curl http://localhost:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 期望结果（关键字段+状态码）：
    - 第四步 `200`，`summary` 包含 `total_steps`、`skip_count`、`error_count`、`duration_ms`
  - 标签：P0

- 用例编号：T5-02
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 期望结果（关键字段+状态码）：
    - `404`
  - 标签：P1

- 用例编号：T5-03
  - 角色：学生
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}
    ```
  - 期望结果（关键字段+状态码）：
    - `200`，`evidenceBundleId` 不为空
  - 标签：P1

- 用例编号：T5-04
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/tasks/{task_id}/report
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 期望结果（关键字段+状态码）：
    - 第一步 `200`
    - 第二步 `200`，且 `summary` 包含 `total_steps`、`error_count`、`skip_count`、`duration_ms`
  - 标签：P0

### 任务6（教学前端最小闭环）

- 用例编号：T6-01
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments/{assignment_id}/attempts
    ```
  - 可选界面：`/teaching/assignments`
  - 期望结果（关键字段+状态码）：
    - `200`，出现尝试列表，包含 `attemptIndex` 与 `status`
  - 标签：P0

- 用例编号：T6-02
  - 角色：教师
  - 前置数据/种子命令：`python r-mos-backend/scripts/seed_teaching_demo.py --reset`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 可选界面：`/teaching/attempts/{attempt_id}/evidence`
  - 期望结果（关键字段+状态码）：
    - `200`，页面显示 `summary` 关键字段（`duration_ms` 等）
  - 标签：P1

### 任务8（默认 Postgres 迁移与契约校验）

- 用例编号：T8-01
  - 角色：开发
  - 前置数据/种子命令：`export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`
  - 接口验收（curl）：
    ```bash
    make migrate
    ```
  - 期望结果（关键字段+状态码）：
    - 命令成功完成，无报错
  - 标签：P0

- 用例编号：T8-02
  - 角色：开发
  - 前置数据/种子命令：`export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`
  - 接口验收（curl）：
    ```bash
    make seed-demo
    ```
  - 期望结果（关键字段+状态码）：
    - 输出包含 `作业`、`任务`、`学生` 信息
  - 标签：P0

- 用例编号：T8-03
  - 角色：开发
  - 前置数据/种子命令：`ALLOW_BOOTSTRAP=1`
  - 接口验收（curl）：
    ```bash
    ALLOW_BOOTSTRAP=1 DATABASE_URL=sqlite+aiosqlite:////tmp/rmos_demo.db \\
      r-mos-backend/.venv/bin/python r-mos-backend/scripts/seed_teaching_demo.py --bootstrap --reset
    ```
  - 期望结果（关键字段+状态码）：
    - 输出包含 `作业` 与 `任务`，允许使用临时库
  - 标签：P1

### 任务9（前端环境治理与一键启动）

- 用例编号：T9-01
  - 角色：开发
  - 前置数据/种子命令：无
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/docs
    ```
  - 操作步骤（命令）：
    ```bash
    cd r-mos-frontend
    npm install
    ```
  - 期望结果（关键字段+状态码）：
    - `npm install` 成功完成，无 `EPERM`
    - `curl` 返回 `200`
  - 标签：P0

- 用例编号：T9-02
  - 角色：开发
  - 前置数据/种子命令：`make migrate && make seed-demo`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments
    ```
  - 操作步骤（命令）：
    ```bash
    make dev
    ```
  - 期望结果（关键字段+状态码）：
    - 后端与前端均启动成功
    - `curl` 返回 `200`
  - 标签：P0

- 用例编号：T9-03
  - 角色：学生
  - 前置数据/种子命令：`make seed-demo`
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/attempts/{attempt_id}/evidence
    ```
  - 可选界面：`/teaching/assignments` → `/teaching/attempts/{attempt_id}` → `/teaching/attempts/{attempt_id}/evidence`
  - 期望结果（关键字段+状态码）：
    - `200`，`summary` 包含 `total_steps`、`error_count`、`duration_ms`
  - 标签：P0

### 任务10（前端路径修正与代理分流安装构建）

- 用例编号：T10-01
  - 角色：开发
  - 前置数据/种子命令：系统代理保持开启
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/docs
    ```
  - 操作步骤（命令）：
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
    env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy npm install
    ```
  - 期望结果（关键字段+状态码）：
    - `npm install` 成功完成
    - `curl` 返回 `200`
  - 标签：P0

- 用例编号：T10-02
  - 角色：开发
  - 前置数据/种子命令：已完成 T10-01
  - 接口验收（curl）：
    ```bash
    curl http://localhost:8000/api/v1/assignments
    ```
  - 操作步骤（命令）：
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
    env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy npm run build
    ```
  - 期望结果（关键字段+状态码）：
    - 输出包含 `vite` 构建完成信息
    - 生成 `dist` 目录
    - 若出现 `chunk` 大小超过 `500 kB` 的警告，不判失败
    - `curl` 返回 `200`
  - 标签：P0

### Phase1 UI 冒烟

- 用例编号：UI-01（PASS）
  - 角色：学生/教师
  - 前置数据/种子命令：
    ```bash
    export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
    make migrate
    make seed-demo
    make dev-backend
    make dev-frontend
    ```
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/tasks/4/report
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/13/evidence
    ```
  - UI 路径验收：
    - 打开 `http://localhost:3000/teaching/attempts/13/evidence`
  - 期望结果（关键字段+状态码）：
    - 接口：两次请求均为 `200`
    - 界面：显示 `task_status=completed`、`total_steps=2`、`error_count=0`、`final_score=100`、`is_passed=true`
  - 标签：P0

### 任务11（诊断报告 P0）

- 用例编号：T11-01
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，EvidenceBundle.summary 中 error_count > 0，且 skip_count=0、duration_ms<=5000
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `diagnosis_code=E_ERROR_OCCURRED`
    - `rule_id=R-DIAG-001`
    - `severity=HIGH`
    - `findings` 与 `recommendations` 为数组（可为空）
  - 标签：P0

- 用例编号：T11-02（No match / R-DIAG-000）
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，EvidenceBundle.summary 中 error_count=0、skip_count=0、duration_ms<=5000
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `diagnosis_code=OK`
    - `rule_id=R-DIAG-000`
    - `severity=LOW`
    - `findings` 与 `recommendations` 为数组（可为空）
  - 标签：P0

- 用例编号：T11-03
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，EvidenceBundle.summary 中 skip_count > 0，且 error_count=0、duration_ms<=5000
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `diagnosis_code=E_STEP_SKIPPED`
    - `rule_id=R-DIAG-002`
    - `severity=MEDIUM`
    - `findings` 与 `recommendations` 为数组（可为空）
  - 标签：P0

- 用例编号：T11-04
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，EvidenceBundle.summary 中 duration_ms > 5000，且 error_count=0、skip_count=0
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `diagnosis_code=E_TOO_SLOW`
    - `rule_id=R-DIAG-003`
    - `severity=LOW`
    - `findings` 与 `recommendations` 为数组（可为空）
  - 标签：P0

- 用例编号：T11-05（规则不触发样例）
  - 角色：教师
  - 前置数据/种子命令：复用 T11-02 的 attempt（error_count=0、skip_count=0、duration_ms<=5000）
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - 未触发 R-DIAG-001/002/003（落入 R-DIAG-000）
  - 标签：P0

- 用例编号：T11-06（fallback 兜底）
  - 角色：教师
  - 前置数据/种子命令：教学 attempt，且不存在 evidence_link（允许触发兜底生成）
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `source_refs.attempt_evidence_id` 非空
  - 标签：P0

- 用例编号：T11-07（并发一致性）
  - 角色：教师
  - 前置数据/种子命令：任一教学 attempt（输入源不变）
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    curl --noproxy 127.0.0.1,localhost http://localhost:8000/api/v1/attempts/{attempt_id}/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - 三次均 `200`
    - 三次 `diagnosis_code` 一致
  - 标签：P0

### 任务12（环境阻塞与验收收口）

- 用例编号：T12-UI-01（前端 listen EPERM 复现）
  - 角色：教师
  - 前置数据/种子命令：无
  - 接口验收（命令）：
    ```bash
    python3 -m http.server 18000
    npm run dev -- --host 127.0.0.1 --port 3000
    npm run dev -- --host 127.0.0.1 --port 3100
    npm run dev -- --host 0.0.0.0 --port 55173
    ```
  - 期望结果（关键字段+状态码）：
    - 均报 `EPERM` / `Operation not permitted`
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 阶段3 前端 listen EPERM 根因调查（不可交付 UI）`
  - 标签：P0

- 用例编号：T12-UI-02（UI 冒烟：诊断页 completed attempt）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`17`
  - UI 路径验收：
    - `http://127.0.0.1:55173/teaching/attempts/17/diagnosis`
  - 期望结果（关键字段可见）：
    - diagnosis_code、severity、rule_id 可见
    - findings、recommendations 列表可见（允许空态）
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 P0 UI 冒烟（前端 55173 + 后端 8000）`
  - 标签：P0

- 用例编号：T12-API-01（Phase2 P0 后端诊断与证据 200）
  - 角色：教师
  - 前置数据/种子命令：Phase1 e2e 产物 attempt_id=`16`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/16/diagnosis
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/16/evidence
    ```
  - 期望结果（关键字段+状态码）：
    - 两次均 `200`
    - diagnosis 含 `reportVersion`、`diagnosisCode`、`ruleId`、`severity`、`sourceRefs.attemptEvidenceId`
    - evidence 含 `summary`
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 P0 真实运行验收（后端）`
  - 标签：P0

### 任务13（Phase2 P1 占位扩展点与教师文案）

- 用例编号：T13-API-01（DiagnosisReport v1 占位扩展点字段返回）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`17`；backend_port=`8000`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/17/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - `200`
    - `stepDiagnoses`、`factors`、`attachments` 均为 `[]`
    - `reportVersion`、`attemptId`、`diagnosisCode`、`ruleId`、`severity` 存在
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 P1 验收证据（占位扩展点 + 教师文案）`
  - 标签：P1

- 用例编号：T13-UI-01（诊断页教师文案与空态）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`17`；frontend_port=`55173`
  - UI 路径验收：
    - `http://127.0.0.1:55173/teaching/attempts/17/diagnosis`
  - 期望结果（关键字段可见）：
    - diagnosis_code 显示教师文案“无异常”
    - severity 显示教师文案“低”
    - findings 空态显示“无”
    - recommendations 空态显示“无”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase2 P1 验收证据（占位扩展点 + 教师文案）`
  - 标签：P1

### 任务14（Phase2 P2 步骤诊断下钻）

- 用例编号：T14-API-01（stepDiagnoses 长度与字段）（PASS）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`22`；backend_port=`8000`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/22/evidence
    curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/attempts/22/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - 两次均 `200`
    - evidence `summary.total_steps=2`
    - diagnosis `stepDiagnoses` 长度=2，且包含 `stepIndex`、`stepDiagnosisCode`、`severity`、`ruleId`、`findings`、`recommendations`、`sourceRefs`
  - 证据落点：`docs/testing/TEST_REPORT.md` → `主目录回归验收（Phase2 基线冻结）`
  - 标签：P2

- 用例编号：T14-UI-01（步骤诊断区块下钻）（PASS）
  - 角色：教师
  - 前置数据/种子命令：completed attempt_id=`22`；frontend_port=`55173`
  - UI 路径验收：
    - `http://127.0.0.1:55173/teaching/attempts/22/diagnosis`
  - 期望结果（关键字段可见）：
    - “步骤诊断”区块可见且可展开
    - 显示 2 步（与 summary.total_steps=2 一致）
    - 每步 severity 标签可见（低）
    - 每步展开后 findings/recommendations 空态显示“无”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `主目录回归验收（Phase2 基线冻结）`
  - 标签：P2

### 任务15（Phase3 Step 1 规则真实触发闭环）

- 用例编号：T15-RULE-01（R-DIAG-001 error_count）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`23`
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
    source .venv/bin/activate
    export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
    python scripts/seed_teaching_diagnosis_cases.py --case error
    ```
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/23/evidence
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/23/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/23/diagnosis`
  - 期望结果（关键字段+状态码）：
    - evidence：`200` 且 `summary.error_count>=1`、`summary.total_steps` 可见
    - diagnosis：`200` 且 `ruleId=R-DIAG-001`、`diagnosisCode=E_ERROR_OCCURRED`、`severity=HIGH`
    - UI：教师文案显示“存在错误步骤”，步骤诊断区块可展开且步数与 `total_steps` 一致
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step1 规则命中证据（R-DIAG-001/002/003）`
  - 标签：P3

- 用例编号：T15-RULE-02（R-DIAG-002 skip_count）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`24`
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
    source .venv/bin/activate
    export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
    python scripts/seed_teaching_diagnosis_cases.py --case skip
    ```
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/24/evidence
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/24/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/24/diagnosis`
  - 期望结果（关键字段+状态码）：
    - evidence：`200` 且 `summary.skip_count>=1`、`summary.total_steps` 可见
    - diagnosis：`200` 且 `ruleId=R-DIAG-002`、`diagnosisCode=E_STEP_SKIPPED`、`severity=MEDIUM`
    - UI：教师文案显示“存在跳过步骤”，步骤诊断区块可展开且步数与 `total_steps` 一致
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step1 规则命中证据（R-DIAG-001/002/003）`
  - 标签：P3

- 用例编号：T15-RULE-03（R-DIAG-003 duration_ms）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`25`
    ```bash
    cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
    source .venv/bin/activate
    export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
    python scripts/seed_teaching_diagnosis_cases.py --case slow
    ```
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/25/evidence
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/25/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/25/diagnosis`
  - 期望结果（关键字段+状态码）：
    - evidence：`200` 且 `summary.duration_ms>5000`、`summary.total_steps` 可见（已知口径差异需在报告标注）
    - diagnosis：`200` 且 `ruleId=R-DIAG-003`、`diagnosisCode=E_TOO_SLOW`、`severity=LOW`
    - UI：教师文案显示“步骤耗时偏长”，步骤诊断区块可展开且步数与 `total_steps` 一致
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step1 规则命中证据（R-DIAG-001/002/003）`
  - 标签：P3

### 任务16（Phase3 Step2 触发步骤定位）

- 用例编号：T16-STEPDIAG-01（R-DIAG-001 触发步骤非 OK）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`23`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/23/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/23/diagnosis`
  - 期望结果（关键字段+状态码）：
    - diagnosis：`200` 且 `stepDiagnoses` 至少 1 条 `stepDiagnosisCode != OK`
    - 非 OK 步骤展开后可见 findings “该步骤存在错误”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step2 步骤诊断下钻证据`
  - 标签：P3

- 用例编号：T16-STEPDIAG-02（R-DIAG-002 触发步骤非 OK）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`24`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/24/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/24/diagnosis`
  - 期望结果（关键字段+状态码）：
    - diagnosis：`200` 且 `stepDiagnoses` 至少 1 条 `stepDiagnosisCode != OK`
    - 非 OK 步骤展开后可见 findings “该步骤被跳过”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step2 步骤诊断下钻证据`
  - 标签：P3

- 用例编号：T16-STEPDIAG-03（R-DIAG-003 触发步骤非 OK）（PASS）
  - 角色：教师
  - 前置数据/种子命令：attempt_id=`25`
  - 接口验收（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:8000/api/v1/attempts/25/diagnosis
    ```
  - UI 路径验收：
    - `http://localhost:3000/teaching/attempts/25/diagnosis`
  - 期望结果（关键字段+状态码）：
    - diagnosis：`200` 且 `stepDiagnoses` 至少 1 条 `stepDiagnosisCode != OK`
    - 非 OK 步骤展开后可见 findings “步骤耗时偏长”
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step2 步骤诊断下钻证据`
  - 标签：P3

### 任务17（Phase3 Step3 运行入口稳态化）

- 用例编号：T17-OPS-01（端口降级与开放接口验证）（PASS）
  - 角色：开发
  - 前置条件：主目录后端启动；8000 绑定失败时降级到 18000
  - 验收命令（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:18000/openapi.json | head -n 5
    ```
  - 期望结果（关键字段+状态码）：
    - `HTTP/1.1 200 OK`（或等价 `200`）
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step3 运行入口稳态化证据`
  - 标签：P3
### 任务18（Phase3 Step4 单命令回归）

- 用例编号：T18-AUTO-01（单命令 Phase3 回归）（PASS）
  - 角色：开发
  - 前置条件：后端可启动并生成诊断样本
  - 命令：`bash r-mos-backend/scripts/run_phase3_regression.sh`
  - 期望结果：自动完成启动、seed、采证与文档回填
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step4 单命令回归证据`
  - 标签：P3

### 任务19（Phase3 Step5 全栈端到端回归）

- 用例编号：T19-E2E-API-01（规则命中与步骤诊断 API 回归）（PASS）
  - 角色：开发
  - 前置条件：后端启动；已生成本次回归 attempt_id
  - 实测端口与样本：backend_port=8000，attempt_id error=35 skip=36 slow=37
  - 验收命令（curl）：
    ```bash
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:<BACKEND_PORT>/api/v1/attempts/<A_ERR>/evidence
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:<BACKEND_PORT>/api/v1/attempts/<A_ERR>/diagnosis
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:<BACKEND_PORT>/api/v1/attempts/<A_SKIP>/evidence
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:<BACKEND_PORT>/api/v1/attempts/<A_SKIP>/diagnosis
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:<BACKEND_PORT>/api/v1/attempts/<A_SLOW>/evidence
    curl --noproxy 127.0.0.1,localhost -i http://127.0.0.1:<BACKEND_PORT>/api/v1/attempts/<A_SLOW>/diagnosis
    ```
  - 期望结果（关键字段+状态码）：
    - evidence：`200` 且 `summary.total_steps`、`summary.error_count/skip_count/duration_ms` 可见
    - diagnosis：`200` 且 `ruleId/diagnosisCode/severity` 命中；`stepDiagnoses` 存在非 OK 项
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step5 全栈端到端回归证据`
  - 标签：P3

- 用例编号：T19-E2E-UI-01（诊断页 UI 冒烟）（PASS）
  - 角色：教师
  - 前置条件：前端 dev server 启动；后端可用
  - 实测端口与样本：frontend_port=3000，attempt_id error=35 skip=36 slow=37
  - UI 路径验收：
    - `http://localhost:<FRONTEND_PORT>/teaching/attempts/<A_ERR>/diagnosis`
    - `http://localhost:<FRONTEND_PORT>/teaching/attempts/<A_SKIP>/diagnosis`
    - `http://localhost:<FRONTEND_PORT>/teaching/attempts/<A_SLOW>/diagnosis`
  - 期望结果：
    - 文案命中：错误/跳过/耗时偏长
    - 步骤诊断区块可展开；触发步骤非 OK 可见
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step5 全栈端到端回归证据`
  - 标签：P3

- 用例编号：T19-E2E-OPS-01（端口策略与入口验证）（PASS）
  - 角色：开发
  - 前置条件：按照 RUNBOOK 启动后端/前端
  - 验收点：
    - 记录实际 `BACKEND_PORT`/`FRONTEND_PORT`（本次为 8000/3000）
    - openapi `200`
  - 证据落点：`docs/testing/TEST_REPORT.md` → `Phase3 Step5 全栈端到端回归证据`
  - 标签：P3

- T18 失败原因：BACKEND_START_FAILED
