# Phase 1：仓库工程化与卫生 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（推荐）逐 Task 实施。步骤用 checkbox（`- [ ]`）跟踪。
>
> 设计 Spec：`docs/superpowers/specs/2026-06-22-quality-hardening-upgrade-design.md`
> 总控计划：`docs/superpowers/plans/2026-06-22-quality-hardening-master-plan.md`

**Goal:** 清理根目录杂物、归档历史文档、删除已合并的遗留分支、修正过期文档指向，使仓库恢复整洁可维护状态。

**Architecture:** 纯工程化清理，不触碰任何应用代码（`r-mos-backend/app`、`r-mos-frontend/src`）。倾向**归档而非删除**；对每个待处理对象先核实其是否被 git 跟踪、是否为有价值产物，再决定 `git mv` / `mv` / `rm`。每个 Task 以「`git status` 状态可验证 + 提交」收尾。

**Tech Stack:** git、shell。无测试框架（清理任务以状态核对替代单测）。

## Global Constraints

- **不修改应用代码**：`r-mos-backend/app/**`、`r-mos-frontend/src/**` 全程零改动。
- **归档优先**：能归档进 `docs-archive/` 的不直接删除；确属可弃产物（构建缓存、临时文件）才删。
- **未自创产物先核实**：移动/删除前确认对象内容，发现与描述不符则停下来上报，不擅自处理。
- 所有提交信息使用中文 + 结尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- 当前在 `main` 分支；本 Phase 清理操作直接在 main 进行（均为可逆的归档/分支删除）。

## 现状事实（执行前已核实，2026-06-22）

- 根目录杂物文件：
  - 未被 git 跟踪：`R-MOS 数字孪生维保智能体功能介绍.docx`、`全国高校名单.xls`
  - 已被 git 跟踪：`add_rmos_to_ppt.py`、`reorder_pptx.py`、`reorder_slides.py`
  - 散落重构方案 `.md`：`R-MOS-前端重构方案-v1.0.md`、`R-MOS_Frontend_Redesign_Plan.md`、`R-MOS_Review_Test_Cleanup_Plan.md`、`R-MOS_Transformation_Plan_V1.0.md`、`数字孪生维保智能体（R-MOS）.md`、`注册、用户管理与权限体系（R-MOS）.md`
  - 保留（工程必需）：`AGENTS.md`、`CLAUDE.md`、`PROJECT_MANUAL.md`、`README.md`
- `DEVELOPMENT_LOG.md`（根，583KB）与 `docs-archive/DEVELOPMENT_LOG.md` 同名并存——需核实差异后合并。
- 根级 `__pycache__/` **未被 git 跟踪**（无需 git rm，仅本地删除 + gitignore 确认）。
- 已合并入 main、可安全删除的本地分支：`mvp-skeleton`、`feat/phase1-teaching-p0`、`feat/sopScripts-adj`、`chore-run-and-clean`、`codex/robot-project-pipeline-exec`
- **未合并、需保留**的本地分支：`feat/sop-adj-structure`、`codex/publish-current-state`

---

### Task 1：归档散落的历史方案文档

**Files:**
- Move: 6 个根目录 `.md` 方案文档 → `docs-archive/`
- 不动：`AGENTS.md`、`CLAUDE.md`、`PROJECT_MANUAL.md`、`README.md`

**Interfaces:**
- Produces: `docs-archive/` 下新增 6 个历史方案文档；根目录不再有散落方案 md。

- [ ] **Step 1：确认目标文件存在且为历史方案（非现行文档）**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos
ls -1 "R-MOS-前端重构方案-v1.0.md" "R-MOS_Frontend_Redesign_Plan.md" "R-MOS_Review_Test_Cleanup_Plan.md" "R-MOS_Transformation_Plan_V1.0.md" "数字孪生维保智能体（R-MOS）.md" "注册、用户管理与权限体系（R-MOS）.md"
```
Expected: 6 个文件均列出。若某个不存在或内容明显是现行文档（被 CLAUDE.md 引用），停下来上报。

- [ ] **Step 2：核对是否被 git 跟踪（决定用 git mv 还是 mv）**

Run:
```bash
git ls-files -- "R-MOS-前端重构方案-v1.0.md" "R-MOS_Frontend_Redesign_Plan.md" "R-MOS_Review_Test_Cleanup_Plan.md" "R-MOS_Transformation_Plan_V1.0.md" "数字孪生维保智能体（R-MOS）.md" "注册、用户管理与权限体系（R-MOS）.md"
```
Expected: 输出已跟踪的子集（可能为空或部分）。跟踪的用 `git mv`，未跟踪的用 `mv`。

- [ ] **Step 3：移动到 docs-archive/**

```bash
mkdir -p docs-archive/root-plans-archive
for f in "R-MOS-前端重构方案-v1.0.md" "R-MOS_Frontend_Redesign_Plan.md" "R-MOS_Review_Test_Cleanup_Plan.md" "R-MOS_Transformation_Plan_V1.0.md" "数字孪生维保智能体（R-MOS）.md" "注册、用户管理与权限体系（R-MOS）.md"; do
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then git mv "$f" docs-archive/root-plans-archive/; else mv "$f" docs-archive/root-plans-archive/; fi
done
```

- [ ] **Step 4：验证根目录只剩保留的 md**

Run: `ls -1 *.md`
Expected: 仅 `AGENTS.md`、`CLAUDE.md`、`PROJECT_MANUAL.md`、`README.md`（外加本 Phase 未涉及的，如有则保持）。`DEVELOPMENT_LOG.md` 留待 Task 3 处理。

- [ ] **Step 5：提交**

```bash
git add -A docs-archive/root-plans-archive
git commit -m "chore: 归档根目录散落的历史方案文档至 docs-archive

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2：清理根目录二进制与 PPT 脚本杂物

**Files:**
- Move tracked: `add_rmos_to_ppt.py`、`reorder_pptx.py`、`reorder_slides.py` → `scripts/legacy-ppt/`
- Move untracked: `R-MOS 数字孪生维保智能体功能介绍.docx`、`全国高校名单.xls` → `docs-archive/assets/`

**Interfaces:**
- Produces: 根目录无 `.py`/`.docx`/`.xls` 杂物；脚本归入 `scripts/legacy-ppt/`，素材归入 `docs-archive/assets/`。

- [ ] **Step 1：确认目标存在**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos
ls -1 add_rmos_to_ppt.py reorder_pptx.py reorder_slides.py "R-MOS 数字孪生维保智能体功能介绍.docx" "全国高校名单.xls"
```
Expected: 5 个文件均列出。

- [ ] **Step 2：移动已跟踪的 PPT 脚本（git mv）**

```bash
mkdir -p scripts/legacy-ppt
git mv add_rmos_to_ppt.py reorder_pptx.py reorder_slides.py scripts/legacy-ppt/
```

- [ ] **Step 3：移动未跟踪的二进制素材（普通 mv）**

```bash
mkdir -p docs-archive/assets
mv "R-MOS 数字孪生维保智能体功能介绍.docx" "全国高校名单.xls" docs-archive/assets/
```

- [ ] **Step 4：验证根目录已无这些杂物**

Run: `ls -1 *.py *.docx *.xls 2>/dev/null || echo "clean"`
Expected: 输出 `clean`（根目录已无 py/docx/xls）。

- [ ] **Step 5：提交**

```bash
git add -A scripts/legacy-ppt
git commit -m "chore: 归集 PPT 脚本至 scripts/legacy-ppt，素材移入 docs-archive/assets

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
> 注：docx/xls 未被 git 跟踪，移动不产生 git 变更，无需 add。

---

### Task 3：合并 DEVELOPMENT_LOG.md 重复副本

**Files:**
- Compare: 根 `DEVELOPMENT_LOG.md`（583KB） vs `docs-archive/DEVELOPMENT_LOG.md`
- 结果：保留一份权威副本于 `docs-archive/`，根目录移除

**Interfaces:**
- Produces: `docs-archive/DEVELOPMENT_LOG.md` 为唯一权威开发日志；根目录无 `DEVELOPMENT_LOG.md`。

- [ ] **Step 1：核对两份差异**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos
wc -l DEVELOPMENT_LOG.md docs-archive/DEVELOPMENT_LOG.md
diff -q DEVELOPMENT_LOG.md docs-archive/DEVELOPMENT_LOG.md && echo "IDENTICAL" || echo "DIFFERENT"
```
Expected: 给出两者行数与是否一致。

- [ ] **Step 2：按差异决定处理**

- 若 `IDENTICAL`：根目录这份为冗余副本，直接移除（见 Step 3）。
- 若 `DIFFERENT`：根目录这份较新且更完整（583KB）。用根目录版本覆盖归档版本：
```bash
cp DEVELOPMENT_LOG.md docs-archive/DEVELOPMENT_LOG.md
```
然后移除根目录版本（Step 3）。若发现归档版本反而包含根目录版本没有的内容，停下来上报，不擅自覆盖。

- [ ] **Step 3：移除根目录副本**

```bash
if git ls-files --error-unmatch DEVELOPMENT_LOG.md >/dev/null 2>&1; then git rm DEVELOPMENT_LOG.md; else rm DEVELOPMENT_LOG.md; fi
```

- [ ] **Step 4：验证**

Run: `ls DEVELOPMENT_LOG.md 2>/dev/null || echo "removed from root"; ls -la docs-archive/DEVELOPMENT_LOG.md`
Expected: 根目录已移除；`docs-archive/DEVELOPMENT_LOG.md` 存在。

- [ ] **Step 5：提交**

```bash
git add -A DEVELOPMENT_LOG.md docs-archive/DEVELOPMENT_LOG.md
git commit -m "chore: 合并 DEVELOPMENT_LOG 重复副本，唯一权威版本归于 docs-archive

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4：gitignore 加固与构建缓存清理

**Files:**
- Modify: `.gitignore`
- Delete (本地，未跟踪): 根级 `__pycache__/`

**Interfaces:**
- Produces: `__pycache__`、常见临时/构建产物在 `.gitignore` 中被忽略；本地缓存目录清除。

- [ ] **Step 1：核对 .gitignore 现状**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos
grep -nE '__pycache__|\.DS_Store|\.pyc|node_modules|dist|\.worktrees' .gitignore || echo "missing entries"
```
Expected: 列出已有忽略项；缺失的在 Step 2 补。

- [ ] **Step 2：补齐缺失的忽略项（仅补不存在的）**

将以下条目中 `.gitignore` 尚未包含的，追加到文件末尾（逐条 grep 确认不存在再加，避免重复）：
```
__pycache__/
*.pyc
.DS_Store
.worktrees/
```
> `node_modules/`、`dist/` 通常已在 frontend/backend 各自 .gitignore；若根 .gitignore 缺失且仓库根曾出现这些产物，一并补上。

- [ ] **Step 3：删除根级构建缓存（未被 git 跟踪）**

```bash
rm -rf __pycache__
```

- [ ] **Step 4：验证 git status 不再有缓存噪声**

Run: `git status --short | grep -E '__pycache__|\.pyc|\.DS_Store' || echo "no cache noise"`
Expected: 输出 `no cache noise`。

- [ ] **Step 5：提交**

```bash
git add .gitignore
git commit -m "chore: 加固 .gitignore，忽略 __pycache__/.DS_Store/.worktrees 等缓存

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5：删除已合并的遗留本地分支

**Files:** 无文件改动（git 分支操作）。

**Interfaces:**
- Produces: 仅保留 `main` 与 2 个未合并分支（`feat/sop-adj-structure`、`codex/publish-current-state`）。

- [ ] **Step 1：再次确认各分支合并状态（防止执行期已变化）**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos
for b in mvp-skeleton feat/phase1-teaching-p0 feat/sopScripts-adj chore-run-and-clean codex/robot-project-pipeline-exec; do
  git merge-base --is-ancestor "$b" main && echo "MERGED: $b" || echo "NOT-MERGED(SKIP): $b";
done
```
Expected: 全部 `MERGED`。任何 `NOT-MERGED` 的分支跳过、不删除并上报。

- [ ] **Step 2：删除已合并分支**

```bash
for b in mvp-skeleton feat/phase1-teaching-p0 feat/sopScripts-adj chore-run-and-clean codex/robot-project-pipeline-exec; do
  git branch -d "$b";
done
```
> 用 `-d`（非 `-D`）：若 git 拒绝删除说明未完全合并，应停下核查而非强删。

- [ ] **Step 3：验证剩余分支**

Run: `git branch`
Expected: 仅剩 `* main`、`feat/sop-adj-structure`、`codex/publish-current-state`。

- [ ] **Step 4：无需提交（分支操作不产生工作树变更）**

记录结果即可，进入 Task 6。

---

### Task 6：修正 CLAUDE.md 过期文档指向并校验

**Files:**
- Modify: `CLAUDE.md`（仅修正失效链接/路径，不改架构内容）

**Interfaces:**
- Consumes: Task 1–5 完成后的新目录结构。
- Produces: CLAUDE.md 中所有引用的文件路径均有效。

- [ ] **Step 1：提取 CLAUDE.md 中引用的文件路径并校验存在性**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos
grep -oE '`[^`]+\.(md|py|ts|tsx|json|yml)`' CLAUDE.md | tr -d '`' | sort -u | while read p; do [ -e "$p" ] && echo "OK   $p" || echo "MISS $p"; done
```
Expected: 列出每个引用路径的存在状态。重点关注 `MISS` 项。

- [ ] **Step 2：逐个修正 MISS 路径**

对每个 `MISS`：
- 若该文件在本 Phase 被移动（如方案文档移入 `docs-archive/`），更新为新路径。
- 若文件本就不存在且无对应物，删除该失效引用或标注为历史。
- 不改动 CLAUDE.md 的架构/进度描述，仅修链接。

- [ ] **Step 3：复验所有引用均有效**

Run:（同 Step 1 命令）
Expected: 不再有 `MISS`（或剩余 MISS 已确认为有意保留的历史引用并在上报中说明）。

- [ ] **Step 4：最终整洁度校验**

Run:
```bash
ls -1 *.md *.py *.docx *.xls 2>/dev/null; echo "---"; git status --short | head
```
Expected: 根目录仅保留 `AGENTS.md`/`CLAUDE.md`/`PROJECT_MANUAL.md`/`README.md`；工作树无意外残留。

- [ ] **Step 5：提交**

```bash
git add CLAUDE.md
git commit -m "docs: 修正 CLAUDE.md 中因仓库清理而失效的文档指向

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 1 收尾（最后一个 Task 完成后）

- [ ] 更新总控计划 `2026-06-22-quality-hardening-master-plan.md`：Phase 1 状态 → ✅ Done。
- [ ] 更新 `CLAUDE.md` 若有结构性变化需反映。
- [ ] 更新记忆：在 `MEMORY.md` 增加质量硬化升级项目条目并写入对应记忆文件。
- [ ] 用中文向用户汇报 Phase 1 成果与下一步（进入 Phase 2 测试安全网）。

## 自检（计划编写完成后）

- **Spec 覆盖**：Spec Phase 1 列出的「根目录清理 / 大日志治理 / 遗留分支清理 / 文档结构统一 / gitignore 加固」分别对应 Task 1+2 / Task 3 / Task 5 / Task 6 / Task 4，全覆盖。
- **占位符**：无 TBD/TODO；每步均含具体命令与预期输出。
- **一致性**：分支名、文件名在各 Task 间一致；保留分支（`feat/sop-adj-structure`、`codex/publish-current-state`）在事实区与 Task 5 一致。
