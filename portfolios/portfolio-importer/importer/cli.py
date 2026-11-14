"""コマンド本体: コピー → 検出 → フロントエンド登録 → バックエンドのモックの雛形作成 → 掲載 md 作成。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from importer import PortfolioError
from importer.content import write_portfolio_md
from importer.copier import copy_tree, resolve_target
from importer.detect import detect_backend, detect_frontend
from importer.frontend import register_frontend
from importer.mock import extract_routes

_SITE_URL = re.compile(r"^https?://[^\s/?#]+(?:/[^\s?#]*)?$")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="add_portfolio.py",
                                description="指定したプロジェクトをポートフォリオとして取り込む")
    p.add_argument("source", help="取り込むプロジェクトのディレクトリ")
    p.add_argument("--slug", help="スラッグ（省略時はディレクトリ名から作る）")
    p.add_argument("--site-url", help="ポートフォリオサイトの URL（例 https://portfolio.example.com）")
    return p


def _rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def run_import(args: argparse.Namespace, repo_root: Path, today: date) -> dict:
    if args.site_url is not None and not _SITE_URL.match(args.site_url):
        raise PortfolioError("--site-url は http:// または https:// で始まる URL にしてください")
    target = resolve_target(Path(args.source), repo_root, args.slug)
    warnings: list[str] = []
    if target.copy_from is not None:
        copy_tree(target.copy_from, target.project_dir)
    project = target.project_dir

    frontend = detect_frontend(project, target.slug, require_lockfile=True)
    backend = detect_backend(project, frontend)
    routes: list = []
    if backend is not None:
        # バックエンドの配下にあるフロントエンド（ルートにバックエンドがある場合など）の API 呼び出しを拾わない
        inner = [frontend.dir] if frontend is not None and backend.dir in frontend.dir.parents else []
        routes = extract_routes(backend, exclude=inner)
    frontend_out = None
    registered = False
    if frontend is not None:
        # ルートにフロントエンドがある場合に、バックエンドまで apps/ にコピーしないようにする
        exclude = [backend.dir] if backend is not None and frontend.dir in backend.dir.parents else []
        # バックエンドは配信できないため、ブラウザ内で応答するモックに置き換える
        registered, w, mock_path = register_frontend(frontend, target.slug, repo_root, project, exclude=exclude,
                                                     mock_routes=routes if backend is not None else None)
        warnings += w
        if registered and backend is not None and backend.dir == frontend.dir:
            warnings.append("フロントエンドとバックエンドが同じディレクトリにあるため、portfolio-site/apps/ にバックエンドの"
                            "ファイルも含まれています。不要なファイルは apps/ から削除してください")
        frontend_out = {"dir": _rel(frontend.dir, repo_root), "kind": frontend.kind, "registered": registered,
                        "mock": _rel(mock_path, repo_root) if mock_path else None}

    backend_out = None
    if backend is not None:
        backend_out = {"dir": _rel(backend.dir, repo_root), "kind": backend.kind, "routes": len(routes)}

    tags: list[str] = []
    for t in (frontend.tags if frontend else []) + (backend.tags if backend else []):
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


def main(argv: list[str], repo_root: Path, today: date | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_import(args, repo_root.resolve(), today or date.today())
    except PortfolioError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
