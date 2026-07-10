# P1-3（CD + 环境分离）移交备注 — 来自 P1-2 终审（2026-07-10）

> 写 P1-3 子计划前必读。S3 生产化的环境/部署层面契约。

1. **凭据管理**：`S3_ACCESS_KEY_ID/S3_SECRET_ACCESS_KEY` 目前 compose env 明文（dev 默认 rmos-minio/rmos-minio-secret）。生产走 secrets 管理；**AWS 上建议留空 access_key 走 IAM 实例角色**（代码已支持：access_key 为空时 boto3 走默认凭据链）。
2. **桶策略与预建**：生产**必须预建桶**+最小权限策略（Get/Put/Delete/List 限定该桶）；勿依赖 `_ensure_bucket` 自动建桶——非 us-east-1 区 create_bucket 缺 LocationConstraint 会失败，且生产账号不应有 CreateBucket 权限。
3. **桶 CORS（关键，Important B）**：浏览器经 307 直连对象存储是跨域请求。MinIO 默认放行掩盖，**AWS S3/OSS 必须显式配桶 CORS**（AllowedOrigins=应用域名，AllowedMethods=GET）否则前端 GLTFLoader/fetch 跟随被拦。**staging 验收必须含一次真浏览器加载 3D 资产的 E2E**（补 P1-2 验收弱化的缺口）。
4. **STORAGE_BACKEND 切换**：`get_storage()` lru_cache 进程单例 + robots.py/worker.py 模块级捕获——切后端必须重启进程（滚动部署满足，热改 env 无效）。S3 模式启动时 head_bucket（网络调用），对象存储不可达会启动失败，readiness 编排要覆盖（compose 已 depends_on healthy，K8s 需等效）。
5. **presign 双端点**：`S3_ENDPOINT_URL`（后端内网）与 `S3_PUBLIC_ENDPOINT_URL`（浏览器可达，参与 SigV4 签名）必须分别配；host 参与签名，配错则 presign 403。`S3_PRESIGN_EXPIRE_SECONDS` 默认 900s，CDN 勿缓存 307。
6. **worker 部署形态（Important A）**：分析管线在 API 同进程同事件循环做同步存储 IO——生产建议把 AnalysisWorker 拆独立进程/容器（同镜像不同 entrypoint），隔离阻塞 + 为横向扩容铺路。已入路线图技术债表。
7. **镜像依赖分离（Minor F）**：生产镜像当前装入 moto（测试库）——CD 镜像考虑 requirements/requirements-dev 分离。
8. **数据迁移**：local→s3 无存量迁移工具；已有本地资产的环境切 S3 前需一次性 `aws s3 sync`/`mc mirror data/robot-assets/` 到桶（key 布局=目录布局，可直接镜像）。
9. **compose 遗留**：`version: "3.8"` 过时警告 + backend 无条件 depends_on minio（local 模式也等 minio 健康）——重构 compose 时一并清理。
