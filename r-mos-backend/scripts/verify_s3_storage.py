# r-mos-backend/scripts/verify_s3_storage.py
"""S3 存储链路验收：对真实 S3/MinIO 跑全部原语 + 预签名 URL 直连下载。

用法（MinIO 已起）：
    S3_ENDPOINT_URL=http://localhost:9000 S3_PUBLIC_ENDPOINT_URL=http://localhost:9000 \
    S3_ACCESS_KEY_ID=rmos-minio S3_SECRET_ACCESS_KEY=rmos-minio-secret \
    python scripts/verify_s3_storage.py
"""
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.storage.s3_storage import S3FileStorage  # noqa: E402

ROBOT_ID = 999901  # 验收专用 id，避免撞真实数据


def main() -> int:
    storage = S3FileStorage(
        bucket=os.environ.get("S3_BUCKET", "rmos-assets"),
        endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
        public_endpoint_url=os.environ.get("S3_PUBLIC_ENDPOINT_URL"),
        access_key=os.environ.get("S3_ACCESS_KEY_ID", ""),
        secret_key=os.environ.get("S3_SECRET_ACCESS_KEY", ""),
        region=os.environ.get("S3_REGION", "us-east-1"),
    )
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    print("== S3 存储链路验收 ==")
    rel = storage.upload(ROBOT_ID, "probe.glb", b"probe-bytes", subdirectory="models")
    check("upload 返回契约格式", rel == f"{ROBOT_ID}/models/probe.glb")
    check("exists 可见", storage.exists(ROBOT_ID, "models/probe.glb"))
    check("download 回读一致", storage.download(ROBOT_ID, "models/probe.glb") == b"probe-bytes")
    check("list_files 含对象", "models/probe.glb" in storage.list_files(ROBOT_ID))

    url = storage.get_public_url(ROBOT_ID, "models/probe.glb")
    check("presigned URL 生成", bool(url))
    try:
        body = urllib.request.urlopen(url, timeout=10).read()
        check("presigned URL 直连下载一致", body == b"probe-bytes")
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] presigned URL 直连下载: {exc}")
        failures.append("presigned-fetch")

    with storage.materialize(ROBOT_ID, "models/probe.glb") as p:
        check("materialize 内容一致", p.read_bytes() == b"probe-bytes")
    with storage.materialize_dir(ROBOT_ID) as d:
        check("materialize_dir 结构完整", (d / "models" / "probe.glb").exists())

    storage.delete(ROBOT_ID, "models/probe.glb")
    check("delete 后不可见", not storage.exists(ROBOT_ID, "models/probe.glb"))

    print("== 结果:", "全部通过 ✅" if not failures else f"失败 {len(failures)} 项 ❌", "==")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
