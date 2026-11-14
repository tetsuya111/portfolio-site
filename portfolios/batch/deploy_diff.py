"""ビルド成果物のフォルダと S3 を内容（MD5）で比べ、変わったファイルだけを送り、そのパスだけ CloudFront を無効化する。

使い方（環境変数）:
  DIST_DIR=dist BUCKET=<バケット> [PREFIX=<バケット内のパス>] [DISTRIBUTION_ID=<ID>] \
  [DELETE_REMOVED=true] [DRY_RUN=true] python deploy_diff.py

- 比較は S3 の ETag（put_object で1回で送ったオブジェクトは MD5 と一致する）で行う。
  マルチパートで送られたオブジェクトは一致しないため、送り直される（結果は正しい）。
- PREFIX はバケット内の置き場所。CloudFront がそこをドメイン直下として配信する前提で、無効化のパスには付けない。
- DELETE_REMOVED が true でなければ、フォルダに無いオブジェクトは消さない（一覧に表示するだけ）。
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import sys
import time
from pathlib import Path

MAX_INVALIDATION_PATHS = 100
IMMUTABLE_PREFIX = "_astro/"  # ファイル名に内容のハッシュが付くアセット

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/manifest+json", ".webmanifest")


def md5_of(path: Path) -> str:
    h = hashlib.md5()  # noqa: S324（内容の比較用。セキュリティ用途ではない）
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def content_type(rel: str) -> str:
    ctype = mimetypes.guess_type(rel)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/json", "application/xml", "image/svg+xml", "application/manifest+json"):
        ctype += "; charset=utf-8"
    return ctype


def cache_control(rel: str) -> str:
    if rel.startswith(IMMUTABLE_PREFIX):
        return "public, max-age=31536000, immutable"
    return "public, max-age=0, must-revalidate"


def invalidation_paths(rel: str) -> list[str]:
    """articles/foo/index.html → /articles/foo/index.html と /articles/foo/"""
    p = "/" + rel
    if p.endswith("/index.html"):
        return [p, p[: -len("index.html")]]
    return [p]


def list_remote(s3, bucket: str, key_prefix: str) -> dict[str, str]:
    """相対パス → ETag。"""
    remote: dict[str, str] = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=key_prefix):
        for obj in page.get("Contents", []):
            remote[obj["Key"][len(key_prefix) :]] = obj["ETag"].strip('"')
    return remote


def deploy(
    s3,
    cf,
    *,
    dist: Path,
    bucket: str,
    prefix: str,
    distribution_id: str | None,
    delete_removed: bool,
    dry_run: bool,
    log=print,
) -> dict:
    key_prefix = f"{prefix.strip('/')}/" if prefix.strip("/") else ""
    remote = list_remote(s3, bucket, key_prefix)
    local: set[str] = set()
    changed: list[str] = []

    for path in sorted(p for p in dist.rglob("*") if p.is_file()):
        rel = path.relative_to(dist).as_posix()
        local.add(rel)
        if remote.get(rel) == md5_of(path):
            continue
        changed.append(rel)
        log(f"upload: {rel}")
        if not dry_run:
            # put_object は1回のリクエストで送るので、ETag が MD5 になる（次回の比較に使える）
            with path.open("rb") as f:
                s3.put_object(
                    Bucket=bucket,
                    Key=key_prefix + rel,
                    Body=f,
                    ContentType=content_type(rel),
                    CacheControl=cache_control(rel),
                )

    removed = sorted(set(remote) - local)
    for rel in removed:
        log(f"{'delete' if delete_removed else 'stale (not deleted)'}: {rel}")
    if delete_removed and removed and not dry_run:
        for i in range(0, len(removed), 1000):  # 1回の削除は最大 1000 件
            s3.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": key_prefix + k} for k in removed[i : i + 1000]], "Quiet": True},
            )

    targets = [
        p
        for rel in changed + (removed if delete_removed else [])
        if not rel.startswith(IMMUTABLE_PREFIX)  # 新しい内容は新しい名前になるので無効化は要らない
        for p in invalidation_paths(rel)
    ]
    invalidated: list[str] = []
    if targets and distribution_id and not dry_run:
        invalidated = ["/*"] if len(targets) > MAX_INVALIDATION_PATHS else targets
        cf.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "CallerReference": f"deploy-diff-{int(time.time() * 1000)}",
                "Paths": {"Quantity": len(invalidated), "Items": invalidated},
            },
        )
        log(f"invalidate: {', '.join(invalidated)}")

    log(f"changed={len(changed)} removed={len(removed)} dry_run={dry_run}")
    return {"changed": len(changed), "removed": len(removed), "invalidated": invalidated}


def main(env: dict) -> int:
    import boto3  # 差分デプロイのときだけ必要（テスト・記事作成では使わない）

    dist = Path(env.get("DIST_DIR", "dist"))
    if not dist.is_dir():
        print(f"{dist} がありません")
        return 1
    bucket = env.get("BUCKET", "")
    if not bucket:
        print("BUCKET が設定されていません")
        return 1
    deploy(
        boto3.client("s3"),
        boto3.client("cloudfront"),
        dist=dist,
        bucket=bucket,
        prefix=env.get("PREFIX", ""),
        distribution_id=env.get("DISTRIBUTION_ID") or None,
        delete_removed=env.get("DELETE_REMOVED") == "true",
        dry_run=env.get("DRY_RUN") == "true",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(dict(os.environ)))
