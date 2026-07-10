# P1-2（S3FileStorage）移交备注 — 来自 P1-1 终审（2026-07-08）

> ✅ 已被 2026-07-08-p1-2-s3-storage.md 消费（全部 12 条落地或有对应测试）；留档备查。

> 写 P1-2 子计划前必读。来源：P1-1 全分支终审报告（Fable），接口契约全集。

1. **`upload` 返回值格式是硬契约**：必须返回 `"{robot_model_id}/{subdirectory}/{filename}"`（含 id 前缀）。该值直接落 DB `robot_assets.file_path`，所有读取方一律 `file_path.split("/", 1)[-1]` 去首段再回调 storage。格式不一致 = 全管线静默失效。
2. **异常契约（测试已固化）**：缺失文件 → `FileNotFoundError`（download/open_stream/materialize）；路径穿越 → `ValueError`（download/delete/exists/open_stream/materialize，**exists 也是抛而非返回 False**）。S3 key 虽不解析 `..`，但必须主动拒绝含 `..` 的 rel_path 以维持 HTTP 层 400 契约。
3. **同步接口 + anyio.to_thread**：ABC 保持同步（决策记录在 file_storage.py 模块 docstring），S3 内部用 `anyio.to_thread` 包 boto3 阻塞 IO，勿改 async ABC。
4. **open_stream 生命周期**：本地文件靠 GC 兜底可容忍；**S3 StreamingBody 不行**（占连接池）——P1-2 给 `get_robot_asset` 加 `background=BackgroundTask(stream.close)`（顺带修掉 P1-1 台账 Minor #4）。
5. **materialize_dir 语义**：yield 目录须含机器人**全部**资产（assembly_builder rglob 全目录索引）；不存在也要 yield 空目录。S3 下 URDF 装配一次全量拉取——成本已知，接受。
6. **materialize/materialize_dir 只读契约**：全调用点已验证只读；新增管线调用方必须维持"写出一律走 upload"。
7. **get_public_url 存在性语义待定**：S3 预签名不校验对象存在，缺失文件 307 → S3 404。P1-2 决策：presign 前 head 一次（换本服务 404）或接受 S3 侧 404。
8. **单例与配置**：`get_storage()` lru_cache 单例，robots.py/worker.py 模块级捕获——切 `STORAGE_BACKEND` 须重启进程；测试 monkeypatch `robots_ep._storage` 模式保持可用。
9. **强一致性要求**：assembly_builder 依赖 upload 后 exists 可见。AWS S3(2020+)/MinIO/OSS 均强一致。
10. **trimesh eager-load 依赖**：manifest_generator 在 with 块外访问 loaded 对象——自包含 GLB 成立；若支持 .gltf+外部 .bin 会读挂。S3 落地后补集成测试固化。
11. **upload 侧 key 校验缺口**（P1-1 终审 Important 1/2，随 P1-2 修）：S3 upload 对 filename/subdirectory 拒绝路径分隔符与 `..`；assembly_builder 循环内 catch ValueError 降级为 skip 单个 link。本地 LocalFileStorage.upload 同步补齐防护保持对称。
12. **compose 无资产卷挂载**（P0 终审遗留）：容器化部署下本地资产不持久——S3 化的直接动因之一。
