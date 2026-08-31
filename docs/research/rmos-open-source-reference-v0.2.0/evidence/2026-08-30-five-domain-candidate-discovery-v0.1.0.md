# R0 五个未启动研究域候选发现记录

- 版本：0.1.0
- 采集日期：2026-08-30
- 采集时间：2026-08-30T22:49:59+08:00
- 研究范围：D-01、D-02、D-05、D-06、D-07
- 对应阶段：R0
- 依据：董事会方向指令 §7.4～§7.8
- 基线：`audit/phase3-auth-control-realtime` @ `56751f5e959c60dac880f96db8b630ce73f8e75b`
- 结论等级：候选发现证据，不是深度研究、硬门槛通过、数值评分或 R0 批准证据

## 1. 目的与边界

本记录只补五个 `NOT_STARTED` 研究域的第一轮候选发现。它回答“哪些对象值得进入后续深度取证”，不回答“哪个对象已经合格或应被采用”。

本轮遵守以下边界：

1. 只使用项目官方仓库、官方文档、维护组织或基金会项目页作为支持候选加入的来源；
2. 既有种子全部重新定位到一手来源，没有把旧报告中的名称直接当作事实；
3. 未固定目标版本、40 位提交、发布物、依赖图和安全公告全集，因此不判定 OSS-G1～OSS-G6 为 PASS；
4. 未执行 §7.7 深度字段采集、100 分评分或主审/异源复核评分；
5. 查询只覆盖公开搜索结果首屏和已知官方目录入口，没有执行 GitHub Search/API 全分页，因此**不声称搜索饱和**；
6. “去重排除”只表示本轮不把同一项目的组件、文档仓库或示例仓库重复算成独立候选，不等于该项目通过硬门槛后的正式淘汰。

## 2. 查询方法与筛选规则

### 2.1 来源路线

| 路线 | 本轮做法 | 限制 |
|---|---|---|
| GitHub 仓库与公开搜索 | 用项目能力词和官方组织限定词定位仓库；核对仓库 README、架构文件或项目说明 | 只查看首屏结果；没有 Search/API 分页、星标阈值或完整主题导出 |
| 维护组织/基金会目录 | 查看 FastAPI、Django、Moodle、Open edX、Frappe、CNCF、NASA 等官方入口 | 不是所有项目都归属基金会；“官方组织”不能替代治理与活跃度取证 |
| 官方架构/开发资料 | 优先保留能直接说明模块、教学、工作流、遥测或授权语义的官方文档 | 本轮未固定文档提交，后续深研必须固定版本或提交 |
| 既有计划种子 | 对 `candidate-register.yaml` 中五域种子逐个回到官方来源重验，并补足 D-01 的具体对象 | 重新发现不等于旧结论恢复有效 |

### 2.2 加入规则

候选进入本轮“待深研集合”须同时满足：

- 官方项目或维护组织能够定位；
- 官方材料显示其直接覆盖本域至少一项核心能力；
- 能回答至少一个本域对应的 A6 Master 问题；
- 不是另一个已登记候选的文档、插件、示例或客户端重复项；
- 当前没有一手证据足以立即证明它与本域完全无关。

### 2.3 状态词

| 状态 | 含义 |
|---|---|
| `RETAIN_FOR_DEEP_RESEARCH` | 官方来源支持其进入 §7.7 深研；尚未通过任何硬门槛 |
| `OBSERVATION_ONLY_PENDING_G2` | 能提供语义参考，但许可证边界已显出明显限制；在 G2 完成前不得建议引入 |
| `DEDUPED_SUPPORTING_SOURCE` | 是候选的组件、文档或示例，只作为证据，不单列候选 |
| `DEFERRED_ALTERNATE` | 本轮首批名额外发现的相邻对象；后续饱和搜索必须重访 |
| `UNKNOWN` | 证据不足，不能写成否定或通过 |

## 3. 查询记录

所有查询均在 2026-08-30 执行，时间窗为“不限历史、优先当前官方页面”。结果页仅检查公开搜索首屏；没有使用登录态、私有索引或 GitHub API 分页。

| Search_ID | 域 | 查询词（原样） | 来源侧重点 | 首屏处理结果 |
|---|---|---|---|---|
| SR-D01-01 | D-01 | `site:github.com/fastapi full-stack-fastapi-template official repository` | 官方仓库 | 找到 FastAPI 官方全栈模板 |
| SR-D01-02 | D-01 | `site:docs.djangoproject.com reusable applications migrations deployment official Django` | 官方开发文档 | 找到 Django project/app 与迁移入口 |
| SR-D01-03 | D-01 | `site:github.com/cookiecutter/cookiecutter-django official repository production ready Django project` | 社区维护组织仓库 | 找到 Cookiecutter Django |
| SR-D01-04 | D-01 | `site:github.com/zulip/zulip official server architecture Django monolith` | 成熟 Python 系统架构 | 找到 Zulip 服务器与架构说明 |
| SR-D02-01 | D-02 | `site:github.com/moodle/moodle official Moodle repository architecture` | 官方 LMS 仓库 | 找到 Moodle 仓库与架构文档 |
| SR-D02-02 | D-02 | `site:github.com/openedx edx-platform official repository architecture` | 官方 LMS 仓库 | 找到 Open edX 平台和官方架构 |
| SR-D02-03 | D-02 | `site:github.com/frappe/lms official Frappe LMS repository` | 官方 LMS 仓库 | 找到 Frappe Learning |
| SR-D02-04 | D-02 | `site:github.com/instructure/canvas-lms official Canvas LMS repository` | 官方 LMS 仓库 | 找到 Canvas LMS 官方组织与仓库 |
| SR-D05-01 | D-05 | `site:github.com/temporalio/temporal official durable execution repository workflow history retry` | 官方工作流仓库 | 找到 Temporal 与事件历史架构 |
| SR-D05-02 | D-05 | `site:github.com/flowable/flowable-engine official BPMN workflow engine human task` | 官方 BPM 仓库 | 找到 Flowable 与 Human Task API |
| SR-D05-03 | D-05 | `site:github.com/camunda/camunda official workflow engine human task source available license` | 官方编排仓库及许可 | 找到 Camunda 8；许可限制需单列 |
| SR-D05-04 | D-05 | `site:github.com/sartography/SpiffWorkflow official BPMN workflow engine human tasks` | Python BPM 候选 | 找到 SpiffWorkflow |
| SR-D06-01 | D-06 | `site:github.com/open-telemetry/opentelemetry-collector official repository telemetry traces metrics logs` | 官方可观测性仓库 | 找到 OpenTelemetry Collector |
| SR-D06-02 | D-06 | `site:github.com/foxglove/mcap official repository robotics telemetry log format` | 官方机器人日志仓库 | 找到 MCAP |
| SR-D06-03 | D-06 | `site:github.com/rerun-io/rerun official repository robotics visualization recording` | 官方机器人数据仓库 | 找到 Rerun |
| SR-D06-04 | D-06 | `site:github.com/nasa/openmct official repository telemetry visualization` | 官方任务遥测仓库 | 找到 NASA Open MCT |
| SR-D07-01 | D-07 | `site:github.com/keycloak/keycloak official repository identity access management authorization services` | 官方 IAM 仓库 | 找到 Keycloak |
| SR-D07-02 | D-07 | `site:github.com/openfga/openfga official repository relationship based access control` | 官方细粒度授权仓库 | 找到 OpenFGA |
| SR-D07-03 | D-07 | `site:github.com/open-policy-agent/opa official repository policy authorization audit decision logs` | 官方策略引擎仓库 | 找到 OPA |
| SR-D07-04 | D-07 | `site:github.com/casbin/casbin official repository authorization RBAC ABAC domains` | 官方授权库仓库 | 找到 Apache Casbin |
| SR-XF-01 | D-06/D-07 | `site:cncf.io/projects OpenTelemetry official CNCF project` | 基金会目录 | 确认 OpenTelemetry 的 CNCF 项目入口 |
| SR-XF-02 | D-07 | `site:cncf.io/projects Open Policy Agent official CNCF project` | 基金会目录 | 确认 OPA 的 CNCF 项目入口 |
| SR-XF-03 | D-07 | `site:cncf.io/projects Keycloak official CNCF project` | 基金会目录 | 确认 Keycloak 的 CNCF 项目入口 |

## 4. D-01 平台与模块化单体

- A6 映射：M-09、M-10、M-11、M-14、M-15、M-17、M-20、M-21、M-24、M-25
- 本轮结论：发现 4 个值得深研的对象；**合格主/次参考仍为 0（尚未评估，不是淘汰结论）**。

| 候选 | 类型 | 加入理由 | 明确边界 | 一手来源 | 状态 |
|---|---|---|---|---|---|
| FastAPI Full Stack Template | 官方项目模板 | 与 R-MOS 技术栈接近，官方仓库包含后端、前端、容器、部署、测试与持续集成结构，可回答配置、测试和交付边界 | 模板不是成熟业务系统；不能证明模块责任、迁移治理或长期演化做法已经适配 R-MOS | [官方仓库](https://github.com/fastapi/full-stack-fastapi-template)、[FastAPI 项目生成说明](https://fastapi.tiangolo.com/project-generation/) | `RETAIN_FOR_DEEP_RESEARCH` |
| Django | 框架 | 官方教程明确区分 project 与可复用 app，并自带迁移、测试和部署体系；适合研究模块边界与迁移纪律 | 不是现成的 R-MOS 架构母版；框架能力不能代替真实系统的责任拆分证据 | [官方仓库](https://github.com/django/django)、[官方教程：project 与 app](https://docs.djangoproject.com/en/dev/intro/tutorial01/) | `RETAIN_FOR_DEEP_RESEARCH` |
| Cookiecutter Django | 生产项目模板 | 官方仓库声明覆盖生产配置、测试、Docker、环境化设置和多种部署选择，可与 FastAPI 模板形成异栈对照 | Django 技术栈不同；模板选项多不等于单校边缘部署成本低 | [官方仓库](https://github.com/cookiecutter/cookiecutter-django)、[官方文档](https://cookiecutter-django.readthedocs.io/en/latest/) | `RETAIN_FOR_DEEP_RESEARCH` |
| Zulip | 成熟 Python/Django 系统 | 官方架构公开 Django 主应用、实时服务、队列、部署和多租户 realm 边界，是可观察的长期演化单体案例 | 团队聊天业务和规模显著不同；只能研究模块、实时和部署边界，不能照搬领域模型 | [官方仓库](https://github.com/zulip/zulip)、[官方架构说明](https://github.com/zulip/zulip/blob/main/docs/overview/architecture-overview.md) | `RETAIN_FOR_DEEP_RESEARCH` |

去重/筛除记录：

- FastAPI 的项目生成网页是模板的官方入口，不另算候选；状态 `DEDUPED_SUPPORTING_SOURCE`。
- `zulip/zulip-architecture` 是 Zulip 的设计提案仓库，不是独立运行系统；仅作为 Zulip 深研的补充证据，状态 `DEDUPED_SUPPORTING_SOURCE`。
- 搜索结果没有形成“成熟 Python 模块化单体”的完整候选全集；D-01 后续仍需 GitHub API 分页和 Python 生态目录检索。

## 5. D-02 教学与学习管理

- A6 映射：M-08、M-12、M-22、M-23
- 本轮结论：重新定位 3 个既有种子并补入 Canvas LMS，共 4 个待深研对象；**尚无候选被证明合格**。

| 候选 | 类型 | 加入理由 | 明确边界 | 一手来源 | 状态 |
|---|---|---|---|---|---|
| Moodle | 完整 LMS | 官方材料覆盖课程、活动、用户、选课角色、插件、作业和测验等核心教学对象，适合核对学校/班级/角色/作业/成绩语义 | PHP 架构和庞大插件生态与 R-MOS 差异大；GitHub 仓库是官方镜像，后续需同时固定 canonical 版本 | [官方仓库镜像](https://github.com/moodle/moodle)、[官方架构文档](https://docs.moodle.org/dev/Moodle_architecture) | `RETAIN_FOR_DEEP_RESEARCH` |
| Open edX Platform | 完整 LMS/CMS | 官方文档明确 LMS、Studio、模块化单体、独立应用和微前端边界，可研究内容发布、学习尝试和平台拆分 | 官方明确自建生产复杂；不能把大规模在线课程架构直接套到单校机器人教学 | [官方仓库](https://github.com/openedx/openedx-platform)、[官方架构](https://docs.openedx.org/en/latest/developers/references/developer_guide/architecture.html) | `RETAIN_FOR_DEEP_RESEARCH` |
| Frappe Learning | 完整 LMS | 官方仓库列出课程层级、班次、直播课、测验、作业和证书，规模与低门槛自托管方向更接近 R-MOS | 依赖 Frappe 平台；近期安全公告和部署/升级问题必须在 G5 与运行成本字段中核查 | [官方仓库](https://github.com/frappe/lms)、[官方安全页](https://github.com/frappe/lms/security) | `RETAIN_FOR_DEEP_RESEARCH` |
| Canvas LMS | 完整 LMS | Instructure 官方组织将其列为开放 LMS，适合作为课程、作业、评分和集成接口的第四个异源样本 | Ruby 技术栈、部署规模和双重许可相关边界需要后续固定版本核查 | [官方仓库](https://github.com/instructure/canvas-lms)、[官方开发入口](https://instructure.github.io/) | `RETAIN_FOR_DEEP_RESEARCH` |

去重/筛除记录：

- `moodlehq/moodleapp` 只属于 Moodle 移动客户端，不覆盖完整教学主记录；并入 Moodle 支持材料，状态 `DEDUPED_SUPPORTING_SOURCE`。
- `openedx/frontend-platform` 是 Open edX 微前端公共框架，不是独立 LMS；并入 Open edX 支持材料，状态 `DEDUPED_SUPPORTING_SOURCE`。
- 本轮没有检索 Sakai、Chamilo 等其他 LMS 的完整结果，故不得宣称候选饱和或正式淘汰。

## 6. D-05 工作流、审批与状态机

- A6 映射：M-06、M-22
- 本轮结论：发现 4 个覆盖持久执行或人工任务语义的对象；Camunda 8 只保留为许可待核的观察对象。

| 候选 | 类型 | 加入理由 | 明确边界 | 一手来源 | 状态 |
|---|---|---|---|---|---|
| Temporal | 持久执行平台 | 官方架构说明事件历史、重放、重试、幂等/非重试活动和故障恢复，直接对应长流程、恢复与历史问题 | 不是人工审批产品；引入服务会增加运行和学习成本，需和仅借语义严格分开 | [官方仓库](https://github.com/temporalio/temporal)、[官方架构](https://github.com/temporalio/temporal/blob/main/docs/architecture/README.md) | `RETAIN_FOR_DEEP_RESEARCH` |
| Flowable | BPMN/CMMN/DMN 引擎 | 官方说明支持 Human Task、等待状态、任务认领/完成、REST/Java API，可直接研究人工审批和状态历史 | Java/Spring 生态与 R-MOS 不同；不得因 Apache-2.0 顶层许可就跳过依赖和发布物审查 | [官方仓库](https://github.com/flowable/flowable-engine)、[官方 Human Task API 文档](https://github.com/flowable/flowable-engine/blob/main/docs/docusaurus/docs/bpmn/ch04-API.md) | `RETAIN_FOR_DEEP_RESEARCH` |
| Camunda 8 | 流程编排平台 | 官方仓库覆盖 Zeebe、Operate、Tasklist，且 Tasklist 明确处理人工输入，适合做编排/人工任务语义对照 | 官方仓库明确核心组件使用 Camunda License 1.0，仅部分组件 Apache-2.0；在逐文件和部署方式 G2 完成前不得建议引入 | [官方仓库及许可说明](https://github.com/camunda/camunda) | `OBSERVATION_ONLY_PENDING_G2` |
| SpiffWorkflow | Python BPMN/DMN 引擎 | 官方仓库为纯 Python 工作流引擎，支持 BPMN/DMN、子流程、定时器、信号和消息，技术栈更接近 R-MOS | 仍需确认人工任务持久化、恢复、审计、运维和许可证组合；当前只证明值得深研 | [官方仓库](https://github.com/sartography/SpiffWorkflow)、[官方文档](https://www.spiffworkflow.org/) | `RETAIN_FOR_DEEP_RESEARCH` |

去重/筛除记录：

- Temporal 的 SDK、学习教程和文档仓库是同一平台的配套对象，不单列候选；状态 `DEDUPED_SUPPORTING_SOURCE`。
- Camunda Tasklist、Operate、Zeebe 位于同一产品/仓库和许可边界内，不拆成三个候选；状态 `DEDUPED_SUPPORTING_SOURCE`。
- 本轮没有覆盖所有 BPMN/低代码/任务编排项目，尤其未完成 GitHub 与基金会目录分页，因此无路线饱和结论。

## 7. D-06 证据、时间线与可观测性

- A6 映射：M-10、M-11、M-15、M-16、M-17、M-18a、M-18b、M-19、M-20、M-21、M-23、M-24
- 本轮结论：重新定位 4 个互补对象；它们分别偏向信号采集、机器人日志容器、多模态回放和时序可视化，不能用单一总分横排。

| 候选 | 类型 | 加入理由 | 明确边界 | 一手来源 | 状态 |
|---|---|---|---|---|---|
| OpenTelemetry Collector | 遥测采集/处理 | 官方仓库明确统一接收、处理和导出 traces、metrics、logs，且有可扩展组件模型；可回答观测信号和管道责任边界 | 不提供机器人证据文件、业务报告引用或备份恢复闭环；Collector 也不等于完整观测后端 | [官方仓库](https://github.com/open-telemetry/opentelemetry-collector)、[CNCF 项目页](https://www.cncf.io/projects/opentelemetry/) | `RETAIN_FOR_DEEP_RESEARCH` |
| MCAP | 机器人日志格式与库 | 官方仓库说明其是面向 pub/sub 和机器人场景的序列化无关容器格式，支持索引、元数据、附件和多语言库 | 文件格式不负责身份、授权、保留策略、报告引用或观测后端；不能单独解决完整证据链 | [官方仓库](https://github.com/foxglove/mcap)、[官方格式站点](https://mcap.dev/) | `RETAIN_FOR_DEEP_RESEARCH` |
| Rerun | 多模态记录、查询与回放 | 官方仓库明确覆盖机器人多模态数据记录、实时流、回放、查询和可视调试，并可读取 MCAP | 官方声明 API 仍在演化且可能破坏兼容；不应把可视化记录自动当作不可抵赖审计证据 | [官方仓库](https://github.com/rerun-io/rerun)、[官方架构](https://github.com/rerun-io/rerun/blob/main/ARCHITECTURE.md) | `RETAIN_FOR_DEEP_RESEARCH` |
| NASA Open MCT | 时序遥测可视化框架 | 官方 API 支持实时/历史遥测提供者、时间窗口、订阅和多视图时间联动，适合研究时间线与告警展示 | 它是前端任务控制框架，不提供 R-MOS 服务端证据主记录、追踪采集或备份恢复 | [官方仓库](https://github.com/nasa/openmct)、[官方 Telemetry API](https://github.com/nasa/openmct/blob/master/API.md) | `RETAIN_FOR_DEEP_RESEARCH` |

去重/筛除记录：

- `opentelemetry-collector-contrib` 是 Collector 组件集合，不在本轮作为独立平台候选；状态 `DEDUPED_SUPPORTING_SOURCE`。
- `nasa/openmct-heatmap` 是 Open MCT 插件，不是独立证据/可观测性系统；状态 `DEDUPED_SUPPORTING_SOURCE`。
- PostgreSQL 备份恢复指南继续作为规范实践来源保留，但它不是 OSS 软件候选，不进入软件评分；本轮未完成其版本化取证。
- 本轮未形成“备份与恢复主责参考”候选，M-18a 仍是显式缺口。

## 8. D-07 身份、授权与审计

- A6 映射：M-01、M-02、M-04、M-06、M-12、M-13
- 本轮结论：重新定位 4 个互补对象；Keycloak 偏身份，OpenFGA/OPA/Casbin 偏不同授权模型，任何单个候选都尚未证明覆盖身份、对象权限、拒绝审计和多租户全链路。

| 候选 | 类型 | 加入理由 | 明确边界 | 一手来源 | 状态 |
|---|---|---|---|---|---|
| Keycloak | IAM 服务 | 官方材料覆盖用户联合、强认证、用户管理和细粒度授权；授权服务架构明确 PAP/PDP/PEP/PIP 分工 | 外置 IAM 不能自动解决 R-MOS 数据对象归属、业务审批和拒绝审计；部署服务成本需单独评估 | [官方仓库](https://github.com/keycloak/keycloak)、[官方授权架构](https://github.com/keycloak/keycloak/blob/main/docs/documentation/authorization_services/topics/auth-services-architecture.adoc)、[CNCF 项目页](https://www.cncf.io/projects/keycloak/) | `RETAIN_FOR_DEEP_RESEARCH` |
| OpenFGA | 细粒度授权服务/库 | 官方仓库提供关系元组、授权模型、对象级检查、测试工具和多种存储，直接对应跨学校/班级/对象关系授权 | 官方快速启动也明确服务自身需要认证；它不提供登录、身份生命周期或完整审计事实源 | [官方仓库](https://github.com/openfga/openfga)、[官方概念文档](https://openfga.dev/docs/concepts) | `RETAIN_FOR_DEEP_RESEARCH` |
| Open Policy Agent | 通用策略引擎 | 官方项目把策略判定从业务代码分离，适合研究统一决策点、上下文策略和决策日志 | 通用策略语言不提供身份库或对象关系主记录；策略输入、执行点和拒绝审计仍需 R-MOS 自己保证 | [官方仓库](https://github.com/open-policy-agent/opa)、[CNCF 项目页](https://www.cncf.io/projects/open-policy-agent-opa/) | `RETAIN_FOR_DEEP_RESEARCH` |
| Apache Casbin | 授权库 | 官方仓库列出 ACL、RBAC、ABAC、域/租户、资源角色、deny override 等模型，且有 Python 实现路线，适合轻量嵌入比较 | 库本身不负责认证、租户数据主记录或强制审计；策略持久化和跨节点一致性需额外设计 | [官方仓库](https://github.com/apache/casbin)、[官方文档](https://casbin.org/docs/overview) | `RETAIN_FOR_DEEP_RESEARCH` |

去重/筛除记录：

- Keycloak Quickstarts/适配器、OpenFGA sample stores/community 仓库均为各自主项目配套材料，不重复计数；状态 `DEDUPED_SUPPORTING_SOURCE`。
- CNCF 目录还显示 Cedar 等相邻授权项目；本轮四对象首批之外未执行完整比较，记为 `DEFERRED_ALTERNATE`，后续饱和检索必须重访：[CNCF Cedar 项目页](https://www.cncf.io/projects/cedar/)。
- 当前没有任何候选被证明同时解决 M-01、M-02、M-06 和 M-13；P0 参考缺口仍未关闭。

## 9. 跨域去重与候选计数

| 域 | 待深研软件候选 | 观察对象 | 合格候选 | 正式淘汰 | 饱和状态 |
|---|---:|---:|---:|---:|---|
| D-01 | 4 | 0 | 0 | 0 | NOT_REACHED |
| D-02 | 4 | 0 | 0 | 0 | NOT_REACHED |
| D-05 | 3 | 1 | 0 | 0 | NOT_REACHED |
| D-06 | 4 | 0 | 0 | 0 | NOT_REACHED |
| D-07 | 4 | 0 | 0 | 0 | NOT_REACHED |
| 合计 | 19 | 1 | 0 | 0 | NOT_REACHED |

计数规则：Camunda 8 计为一个观察对象；组件、客户端、示例、文档仓库不重复计数。`合格候选=0` 的原因是硬门槛尚未执行完毕，而不是这 20 个对象已经被判不合格。

## 10. 后续必补证据

本文件不能解除 R0 或 R1 门禁。至少还需完成：

1. 对五域执行 GitHub Search/API 和正式项目目录分页，保存页码、总数、去重和停止条件；
2. 为每个候选固定目标版本、40 位提交或发布 tag，并登记不可变证据 URL；
3. 按 §7.7 生成每项目结构化结果，补齐架构、部署、迁移、治理、贡献者、响应样本和领域语义；
4. 逐一完成 OSS-G2 四种使用方式的许可证边界，特别是 Camunda 8、Canvas、Moodle/Frappe 的传播和部署边界；
5. 逐一完成 OSS-G5 的目标版本、支持期、依赖、容器、公告、漏洞库、披露、修复与可利用性取证；
6. 只有全部硬门槛通过者才能进入同域 100 分评分和双人异源校准；
7. D-06 继续发现备份恢复专门候选/规范，D-07 继续发现能同时支撑对象权限和拒绝审计的实现；
8. 本轮 20 个对象已按 `FIRST_PASS_DISCOVERY_COMPLETE` / `RETAIN_FOR_DEEP_RESEARCH` 等非通过状态写入 `candidate-register.yaml`；后续深研、淘汰或升级资格时必须同步更新登记表和原始证据。

## 11. 本轮结论

五个原 `NOT_STARTED` 域已经形成可追溯的第一轮候选发现：每域 4 个对象，共 20 个，其中 19 个进入待深研集合、1 个仅作许可待核的观察对象。查询路线、加入理由、去重理由和官方 URL 已保存。

但搜索未分页、未达到饱和，20 个对象均未完成 OSS-G1～OSS-G6 和 §7.7 深研，因此不能写成“R0 候选完整”“已有合格参考”或“R1 可以开始”。
