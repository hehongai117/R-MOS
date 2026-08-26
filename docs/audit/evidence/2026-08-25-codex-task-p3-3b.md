# 任务：让 3D 资产加载带上认证令牌（R-MOS P3-3b）

你在工作区 `/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`
的分支 `audit/phase3-auth-control-realtime` 上工作。前端目录是 `r-mos-frontend`，
`node_modules` 已安装好，不需要再 `npm install`。

## 背景（事实，已核实）

后端 Phase 3 第 1 批上线了「默认拒绝」认证网关：`r-mos-backend/app/core/public_routes.py`
里 7 条白名单之外的 `/api/v1/**` 路由，无令牌一律 401。机器人资产路由
`GET /api/v1/robots/{id}/assets/{path}` **不在**白名单里。

前端的 `apiClient`（`src/api/client.ts`）会自动挂 `Authorization: Bearer <token>`，
但 `@react-three/drei` 的 `useGLTF` 内部是 `GLTFLoader` 直接发请求，**不走 apiClient、
不带令牌**，所以 3D 网格现在全部 401 加载失败。

本仓装的是 `@react-three/drei@9.122.0`，它的 `useGLTF` 签名是：

```ts
useGLTF(path, useDraco?, useMeshopt?, extendLoader?: (loader: GLTFLoader) => void)
useGLTF.preload(path, useDraco?, useMeshopt?, extendLoader?)
```

`extendLoader` 拿到的 `GLTFLoader` 继承了 three 的 `Loader.setRequestHeader(headers)`，
这就是注入 `Authorization` 头的位置。**这条路径已经验证过存在**，见
`node_modules/@react-three/drei/core/Gltf.d.ts` 与 `Gltf.js`。

## 已经写好的失败测试（**不要修改它的任何断言**）

`r-mos-frontend/src/components/Viewer3D/__tests__/authedGltf.gate.test.ts`

现在是红的。你的任务是让它变绿，**不准改断言、不准删用例、不准放宽正则、
不准往门禁里加豁免名单**。如果你认为某条断言本身写错了，停下来在最终回复里说明，
不要自行修改。

跑它：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-frontend
npx vitest run src/components/Viewer3D/__tests__/authedGltf.gate.test.ts
```

## 要做的事

### 1. 新建 `src/components/Viewer3D/useAuthedGLTF.ts`

一个薄封装，是**全仓唯一**允许直接 import drei `useGLTF` 的文件：

- `useAuthedGLTF(path, useDraco?, useMeshopt?)` → 转调 `useGLTF(path, useDraco, useMeshopt, extendLoader)`
- `useAuthedGLTF.preload(...)` → 同样转调 `useGLTF.preload`，带同一个 `extendLoader`
- `extendLoader` 的行为：取到令牌就 `loader.setRequestHeader({ Authorization: \`Bearer ${token}\` })`；
  **取不到令牌就什么都不做**（不要设空头，不要抛异常）
- 支持 `path` 为 `string` 或 `string[]`（`atom01/SubPartsGroup.tsx` 用数组形式）
- 类型要正确：数组进数组出，单个进单个出（照抄 drei 的条件类型即可）

### 2. 令牌口径必须和 apiClient 完全一致

`src/api/client.ts` 的请求拦截器现在是这样取令牌的：

```ts
const token =
  useAuthStore.getState().accessToken ??
  localStorage.getItem(AUTH_STORAGE_KEYS.accessToken) ??
  localStorage.getItem(AUTH_STORAGE_KEYS.legacyAccessToken)
```

**不要把这三行复制一份到新文件。** 把它提取成一个共享函数（建议
`export function getAccessToken(): string | null` 放在 `src/store/authStore.ts`，
那里已经定义了 `AUTH_STORAGE_KEYS` 且没有循环依赖风险），然后
`client.ts` 和 `useAuthedGLTF.ts` 都调它。`client.ts` 的行为不能变。

### 3. 把 11 个直接 import `useGLTF` 的文件改成用封装

```
Atom01AssemblyRenderer.tsx
Atom01Model.tsx
DetailParts.tsx
DisassemblyAnimation.tsx
InteractiveManifestViewer.tsx
ManifestDrivenRenderer.tsx
ModelPreloader.tsx
PartInspector.tsx
RuntimeAssetPreview.tsx
atom01/InteractiveLinkMesh.tsx
atom01/SubPartsGroup.tsx
```

（路径都相对 `src/components/Viewer3D/`）

这是机械替换：`import { useGLTF } from '@react-three/drei'` →
`import { useAuthedGLTF } from './useAuthedGLTF'`（注意 `atom01/` 下要用 `../useAuthedGLTF`），
调用点 `useGLTF(...)` → `useAuthedGLTF(...)`，`useGLTF.preload(...)` → `useAuthedGLTF.preload(...)`。

注意 `PartInspector.tsx` 是 `import { Center, OrbitControls, useGLTF } from '@react-three/drei'`
这种混合 import，只摘掉 `useGLTF`，其余保留。

其中 3 个文件（`DetailParts` / `DisassemblyAnimation` / `PartInspector`）加载的是前端
静态资源 `/models/parts/*`，不是后端资产。它们**照样要改**——门禁规则是统一的
「Viewer3D 下不得直接用 useGLTF」，多带一个头对同源静态文件无害，比维护一份
豁免名单可靠。

### 4. 把裸 fetch 改成 apiClient

`src/components/Viewer3D/hooks/useAtom01AssemblyData.ts:33` 的
`const response = await fetch(url, { cache: 'no-store' })` 取的是
`/api/v1/robots/{id}/assets/...` 下的 JSON，同样不带令牌。改成用
`apiClient`（`import { apiClient } from '@/api/client'`），保持「不缓存」语义和
原有的错误行为（失败时抛出带 url 和状态码的错误）。

### 5. 修既有测试里的 drei mock

有几个既有测试 mock 了 `@react-three/drei` 的 `useGLTF`，组件改用封装后这些 mock
的挂载点可能要跟着调整（封装内部仍然调 drei 的 `useGLTF`，所以多数 mock 应该仍然生效，
但请实际跑一遍确认）：

```
src/components/Viewer3D/__tests__/PartInspector.test.tsx
src/components/Viewer3D/__tests__/Atom01AssemblyRenderer.test.tsx
src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx
```

允许改这三个文件的 **mock 装配方式**，但**不得改变它们的断言语义**。

## 验证（必须全部实际跑过，把真实输出贴进最终回复）

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-frontend
npx vitest run src/components/Viewer3D/__tests__/authedGltf.gate.test.ts
npx vitest run
npm run build
npx tsc --noEmit
```

四条都要绿。`npx vitest run` 的基线是全绿，不允许留下任何新的红。

## 硬约束

- **不要碰 `r-mos-backend/` 的任何文件。** 这一批是纯前端。
- 不要改 `vite.config.ts` 的 proxy、不要改 CORS、不要改任何 `.env`。
- **不要 git commit，不要 git push，不要建分支。** 改完把工作区留在未提交状态，
  由我来复核 diff 并提交。
- 不要跑 `npm audit`、不要跑 `npm install`、不要装新依赖。
- 不要顺手重构无关代码。改动范围就是上面列的：1 个新文件 + 1 个共享函数提取 +
  11 个替换 + 1 个 fetch 改造 + 最多 3 个测试 mock 调整。
- 不要为了让类型通过就写 `any` / `@ts-ignore`。`npx tsc --noEmit` 必须真的干净。

## 最终回复里要写清楚

1. `git diff --name-only` 的实际输出；
2. 四条验证命令的真实结果（通过数/失败数，不要写"应该通过"）；
3. 你实际遇到的问题和处理方式；
4. 任何你认为断言写错、但按要求没有自行修改的地方。
