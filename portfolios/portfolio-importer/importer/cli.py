"""コマンド本体: コピー → 検出 → フロントエンド登録 → Dockerfile 生成（とイメージ作成） → 掲載 md 作成。"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from importer import PortfolioError
from importer.backend import build_image, write_docker_files
from importer.content import write_portfolio_md
from importer.copier import copy_tree, resolve_target
from importer.detect import detect_backend, detect_frontend
from importer.frontend import register_frontend

_SITE_URL = re.compile(r"^https?://[^\s/?#]+(?:/[^\s?#]*)?$")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="add_portfolio.py",
                                description="指定したプロジェクトをポートフォリオとして取り込む")
    p.add_argument("source", help="取り込むプロジェクトのディレクトリ")
    p.add_argument("--slug", help="スラッグ（省略時はディレクトリ名から作る）")
    p.add_argument("--site-url", help="ポートフォリオサイトの URL（例 https://portfolio.example.com）")
    p.add_argument("--build-image", action="store_true",
                   help="docker でバックエンドのイメージを作成する（ベースイメージを外部から取得する）")
    return p


def _rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def run_import(args: argparse.Namespace, repo_root: Path, run, today: date) -> dict:
    if args.site_url is not None and not _SITE_URL.match(args.site_url):
        raise PortfolioError("--site-url は http:// または https:// で始まる URL にしてください")
    target = resolve_target(Path(args.source), repo_root, args.slug)
    warnings: list[str] = []
    if target.copy_from is not None:
        copy_tree(target.copy_from, target.project_dir)
    project = target.project_dir

    frontend = detect_frontend(project, target.slug)
    frontend_out = None
    registered = False
    if frontend is not None:
        registered, w = register_frontend(frontend, target.slug, repo_root, project)
        warnings += w
        frontend_out = {"dir": _rel(frontend.dir, repo_root), "kind": frontend.kind, "registered": registered}

    backend = detect_backend(project, frontend)
    backend_out = None
    if backend is not None:
        docker = write_docker_files(backend)
        warnings += docker.warnings
        image = None
        if args.build_image and docker.has_cmd:
            image = _rel(build_image(backend.dir, target.slug, repo_root, run=run), repo_root)
        backend_out = {"dir": _rel(backend.dir, repo_root), "kind": backend.kind,
                       "dockerfile": _rel(docker.dockerfile, repo_root), "image": image}

    tags: list[str] = []
    for t in (frontend.tags if frontend else []) + (backend.tags if backend else []) + (["Docker"] if backend else []):
        if t not in tags:
            tags.append(t)
    app_url = f"{args.site_url.rstrip('/')}/apps/{target.slug}/" if args.site_url and registered else None
    content, w = write_portfolio_md(target.slug, project, repo_root, tags, app_url, today)
    warnings += w

    return {
        "slug": target.slug,
        "projectDir": _rel(project, repo_root),
        "copied": target.copy_from is not None,
        "frontend": frontend_out,
        "backend": backend_out,
        "content": _rel(content, repo_root) if content else None,
        "warnings": warnings,
    }


def main(argv: list[str], repo_root: Path, run=subprocess.run, today: date | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_import(args, repo_root.resolve(), run, today or date.today())
    except PortfolioError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
