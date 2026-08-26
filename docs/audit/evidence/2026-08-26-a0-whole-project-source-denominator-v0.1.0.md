# A0 全项目事实源分母证据

- 版本：0.1.0
- 日期：2026-08-26
- 状态：In Review
- 被审系统基线：`29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 审计对象：整个 R-MOS 项目，而不是 Phase 3；Phase 3 只作为额外干预层重验。

## 1. 分母边界

事实源分母由两个不能直接相加的集合组成：

1. `B-ASIS` 中全部 Git 跟踪文件，用于证明仓库内代码、测试、迁移、脚本、资产、配置和文档均已归类；
2. 运行时重新观察的当前事实源，用于证明实际依赖、数据库、路由、配置、进程和存储没有被 Markdown 分母吞掉；其中部分文件也可能受 Git 跟踪，但取证方法与 Git 树异源。

工作目录的简单 `find` 结果不作为分母，因为它会把虚拟环境、依赖目录、缓存、临时文件和构建副作用混入被审对象。Git 文件分母必须由固定提交生成；运行事实源分别保留自己的对象定义、数量、摘要和采集时间。

## 2. Git 跟踪文件分母

使用 [全项目事实源分母枚举脚本](./2026-08-26-a0-whole-project-source-denominator.py) 对 `B-ASIS` 执行互斥分类，分类顺序固定，未分类项会使脚本退出非零。

| Source_Class | 对象 | 数量 | 后续主要阶段 |
|---|---|---:|---|
| application | 后端应用、前端源码和 schema 实现 | 431 | A1、A2、A3、A4 |
| tests | 后端、前端和 E2E 测试 | 229 | A1、A4、A5 |
| migrations | Alembic 版本及迁移运行文件 | 40 | A1、A3、A4、A5 |
| scripts | 项目脚本和 shell 入口 | 37 | A1、A3、A4、A5 |
| assets_modules | public、storage、modules、机器人及 3D 资产 | 850 | A1、A2、A3、A5 |
| config_dependency_generated | 配置、依赖声明及已跟踪生成证据 | 43 | A1、A3、A4、A5 |
| documents_markdown | 现行、历史、计划、报告和模块说明 | 136 | A0–A6 |
| documents_binary | 仓库内 Word/Excel 材料 | 2 | A0、A1、A6 |
| audit_evidence_scripts | 已保全的审计探针 | 1 | A0、A4 |
| **合计** | `B-ASIS` 全部 Git 跟踪文件 | **1,769** | A0–A6 |
| **未分类** | 脚本无法归类的路径 | **0** | 必须保持为 0 |

复现命令：

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
  docs/audit/evidence/2026-08-26-a0-whole-project-source-denominator.py \
  29d2a5889e3b320a3e777e3d8c19efbbe31c0294
```

实际结果：`tracked_files=1769`，九类数量之和为 1769，`unclassified=[]`，退出码 0。

## 3. 运行时重新观察的事实源

这些集合的对象定义不同，不与 1,769 做总和，只作为独立分母逐阶段复比。

| Runtime_Source | 对象定义 | A0 数量/摘要 | 作用 |
|---|---|---|---|
| Python 实际依赖 | 固定解释器的 `pip freeze` 行 | 84 项；摘要 `756df726…63925` | 对照 requirements，识别实际解析漂移 |
| Node 实际依赖 | `npm ls --all --json` 的依赖出现节点 | 1,695 个依赖出现节点；树摘要 `712d753e…15385` | 对照 package/lock，识别实际安装漂移 |
| 数据库结构 | 当前 `rmos` public schema | 66 张表；schema 摘要 `6d43b300…d70` | 对照 ORM、迁移和数据所有权 |
| 数据库扩展 | `pg_extension` | `plpgsql 1.0`、`vector 0.8.2` | 识别运行能力与部署依赖 |
| 后端运行入口 | 导入当前 `main.app` 后的路由注册表 | 181 条 `APIRoute`、187 条总路由 | A1 与源码/OpenAPI 对差集 |
| 运行配置 | `.env` 字段名，不记录值 | 10 个字段名；摘要 `b8ca01f5…6d4a` | 识别字段漂移且不泄露秘密 |
| 本地机器人资产 | `robot-assets` 实际文件清单 | 1 个文件；路径摘要 `807749ea…b8ba` | 对照 Git、manifest 和消费者 |
| 关键本地数据 | `knowledge_store.json` | 摘要 `6d00252d…475f` | 识别审计期间副作用 |
| 数据库规模替代指纹 | 表名及 `pg_stat_user_tables` 统计 | 66 行；摘要 `b25ebdee…bbe0` | 不导出业务值的变化提示，不替代数据一致性审计 |
| 进程与监听 | A0 采集时的本机进程/端口 | 未识别 R-MOS 服务；外部部署 UNKNOWN | 只支持本机时点结论 |
| 工作区非跟踪状态 | A0 启动时 ignored/untracked | ignored 状态条目 42、untracked 0 | 防止只看 Git diff 漏掉运行资产 |

## 4. 使用规则

- A1 先用上述分母形成全系统功能和技术资产清单，不允许只按 Phase 3 发现反推系统范围。
- Git 跟踪文件“已归类”不等于逐文件“已审完”；每阶段按职责消费对应类别。
- 构建产物、缓存或运行时文件若影响功能、交付或恢复，必须进入运行事实源；无关临时文件不得用于做大分母。
- 新增对象进入变化清单，重算所属分母和下游受影响结论。
- 任一类别出现未分类项、差集未解释或运行源缺失时，相关覆盖率不能写 100%。
