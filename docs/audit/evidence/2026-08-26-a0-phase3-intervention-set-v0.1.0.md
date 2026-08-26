# A0 Phase 3 干预层逐提交证据

- 版本：0.1.0
- 日期：2026-08-26
- 状态：In Review
- `B-REF`：`361eaac85002eec4e9388ae4d7f30c2e3591eee6`
- `B-ASIS`：`29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 用途：证明 Phase 3 已经发生的应用与测试修改不会因为进入现状基线而被审计遗漏。

## 1. 形成规则

以 `B-REF..B-ASIS` 的 Git 历史为全集，逐提交检查应用、测试、脚本、迁移、配置和相关文档。应用、测试和脚本变更共 9 个提交、56 个去重文件：应用或运行文件 27 个、测试文件 27 个、脚本 1 个、规则文件 1 个。没有依赖锁文件或迁移文件变化。其间 12 个纯文档提交保留在 Git 全历史中，由 A0 事实源登记处理。

原 Phase 3 计划仍标为 `Planned` 且称未获开工批准，与已经实施的事实冲突；因此下表的“原批准”统一记为“会话批准记录未固化到计划，必须重验”，不得用提交存在本身倒推批准充分。

## 2. 应用、测试和脚本干预提交

| ID | 提交 | 目标 | 当前证据 | 必须重验 |
|---|---|---|---|---|
| INT-001 | `341dc20c` | AUTH-101/102 默认拒绝与公开白名单 | E1；机制已落地，发现未关闭 | A1、A2、A4 |
| INT-002 | `44ed15f7` | 登出公开白名单修正 | E1 | A1、A2、A4 |
| INT-003 | `c26eb183` | 默认拒绝后的测试恢复 | E1；测试变化不等于功能通过 | A1、A2、A4 |
| INT-004 | `6aba328e` | AUTH-104 教学域服务端身份 | E1；AUTH-104 未关闭 | A1、A2、A4 |
| INT-005 | `d18dc5c0` | AUTH-103/105 资产边界、登录限流、邮箱遮蔽 | E1；相关发现未关闭 | A1、A2、A4 |
| INT-006 | `4e6378e8` | 3D 资产令牌加载失败门禁 | E1 | A1、A2、A4 |
| INT-007 | `70e9c078` | 3D 资产带令牌加载 | E1 + 本机开发浏览器；不等于 E2 | A1、A2、A4、A5 |
| INT-008 | `f4c4a752` | AUTH-101 对象归属失败门禁 | E1 | A1、A2、A4 |
| INT-009 | `c7ad217a` | 8 条路由对象归属校验 | E1；AUTH-101 未关闭 | A1、A2、A4 |

### INT-001｜`341dc20c`

```text
r-mos-backend/app/core/public_routes.py
r-mos-backend/app/services/authz_guard.py
r-mos-backend/main.py
r-mos-backend/tests/e2e/test_agent_diagnosis_flow.py
r-mos-backend/tests/test_api_student_robots.py
r-mos-backend/tests/unit/test_auth_boundary.py
```

### INT-002｜`44ed15f7`

```text
r-mos-backend/app/core/public_routes.py
```

### INT-003｜`c26eb183`

```text
r-mos-backend/tests/e2e/conftest.py
r-mos-backend/tests/e2e/helpers.py
r-mos-backend/tests/unit/test_api_training_flow.py
r-mos-backend/tests/unit/test_robot_sop_draft_api.py
r-mos-backend/tests/unit/test_training_characterization.py
r-mos-backend/tests/unit/test_training_phase2_api.py
r-mos-backend/tests/unit/test_training_workbench_draft_api.py
r-mos-backend/tests/unit/test_training_workbench_execution_api.py
```

### INT-004｜`6aba328e`

```text
r-mos-backend/app/api/v1/endpoints/teaching_roster.py
r-mos-backend/app/services/access_control.py
r-mos-backend/app/services/authz_guard.py
r-mos-backend/scripts/run_gate2_smoke.sh
r-mos-backend/tests/e2e/test_e2e_cross_role_access.py
r-mos-backend/tests/unit/test_api_teaching.py
r-mos-backend/tests/unit/test_attempt_replay_api.py
r-mos-backend/tests/unit/test_auth_boundary_gate.py
r-mos-backend/tests/unit/test_evidence_cards_api.py
r-mos-backend/tests/unit/test_teaching_api.py
r-mos-backend/tests/unit/test_teaching_characterization.py
r-mos-backend/tests/unit/test_teaching_identity_boundary.py
```

### INT-005｜`d18dc5c0`

```text
r-mos-backend/app/api/v1/endpoints/auth.py
r-mos-backend/app/api/v1/endpoints/robots.py
r-mos-backend/app/api/v1/endpoints/schools.py
r-mos-backend/app/services/login_throttle.py
r-mos-backend/tests/unit/test_login_throttle.py
r-mos-backend/tests/unit/test_robot_asset_boundary.py
r-mos-backend/tests/unit/test_robot_asset_serving.py
r-mos-backend/tests/unit/test_teaching_identity_boundary.py
```

### INT-006｜`4e6378e8`

```text
r-mos-frontend/src/components/Viewer3D/__tests__/authedGltf.gate.test.ts
```

### INT-007｜`70e9c078`

```text
r-mos-frontend/src/api/client.ts
r-mos-frontend/src/components/Viewer3D/Atom01AssemblyRenderer.tsx
r-mos-frontend/src/components/Viewer3D/Atom01Model.tsx
r-mos-frontend/src/components/Viewer3D/DetailParts.tsx
r-mos-frontend/src/components/Viewer3D/DisassemblyAnimation.tsx
r-mos-frontend/src/components/Viewer3D/InteractiveManifestViewer.tsx
r-mos-frontend/src/components/Viewer3D/ManifestDrivenRenderer.tsx
r-mos-frontend/src/components/Viewer3D/ModelPreloader.tsx
r-mos-frontend/src/components/Viewer3D/PartInspector.tsx
r-mos-frontend/src/components/Viewer3D/RuntimeAssetPreview.tsx
r-mos-frontend/src/components/Viewer3D/__tests__/Atom01AssemblyRenderer.test.tsx
r-mos-frontend/src/components/Viewer3D/__tests__/authedGltf.gate.test.ts
r-mos-frontend/src/components/Viewer3D/atom01/InteractiveLinkMesh.tsx
r-mos-frontend/src/components/Viewer3D/atom01/SubPartsGroup.tsx
r-mos-frontend/src/components/Viewer3D/hooks/__tests__/useAtom01AssemblyData.test.tsx
r-mos-frontend/src/components/Viewer3D/hooks/useAtom01AssemblyData.ts
r-mos-frontend/src/components/Viewer3D/useAuthedGLTF.ts
r-mos-frontend/src/store/authStore.ts
```

### INT-008｜`f4c4a752`

```text
r-mos-backend/tests/e2e/test_object_ownership_boundary.py
```

### INT-009｜`c7ad217a`

```text
r-mos-backend/app/api/v1/endpoints/tasks.py
r-mos-backend/app/api/v1/endpoints/training.py
r-mos-backend/app/services/ownership.py
r-mos-backend/tests/e2e/test_e2e_task_report_evidence.py
r-mos-backend/tests/unit/test_training_characterization.py
r-mos-backend/tests/unit/test_training_phase2_api.py
```

## 3. 相关文档提交

`B-REF..B-ASIS` 还包含 12 个纯文档提交：`b26b86a2`、`69dd5929`、`59f81077`、`08a637b2`、`45d023dd`、`41dd56c0`、`6cb81ada`、`d434d836`、`7e33ea52`、`545cfcfb`、`84e96802`、`29d2a588`。它们分别记录逐批结果、交接、事实更正、中期报告和董事会指令；全部作为事实源输入，不作为应用实现证据。

## 4. 可复现命令

```bash
git log --reverse --format='%H %ad %s' --date=iso-strict 361eaac85002eec4e9388ae4d7f30c2e3591eee6..29d2a5889e3b320a3e777e3d8c19efbbe31c0294
git log --reverse --format='%H %s' 361eaac85002eec4e9388ae4d7f30c2e3591eee6..c7ad217ac6fa15ffc5e26369b4624b93d686041f -- . ':!docs' ':!docs-archive' ':!AGENTS.md' ':!CLAUDE.md' ':!.claude'
git diff --name-only 361eaac85002eec4e9388ae4d7f30c2e3591eee6..c7ad217ac6fa15ffc5e26369b4624b93d686041f -- . ':!docs' ':!docs-archive' ':!AGENTS.md' ':!CLAUDE.md' ':!.claude'
```
