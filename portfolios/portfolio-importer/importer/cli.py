"""コマンド本体: コピー → 検出 → フロントエンド登録 → Dockerfile 生成（とイメージ作成） → 掲載 md 作成。"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from importer import PortfolioError
from importer.backend import build_image, write_docker_files
from importer.content import write_portfolio_md
from importer.copier import copy_tree, resolve_target
from importer.detect import detect_backend, detect_frontend
from importer.envvars import (HTTPS_URL, find_backend_env_names, find_frontend_env_names, frontend_url_env,
                              read_site_url)
from importer.frontend import register_frontend

_SITE_URL = re.compile(r"^https?://[^\s/?#]+(?:/[^\s?#]*)?$")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="add_portfolio.py",
                                description="指定したプロジェクトをポートフォリオとして取り込む")
    p.add_argument("source", help="取り込むプロジェクトのディレクトリ")
    p.add_argument("--slug", help="スラッグ（省略時はディレクトリ名から作る）")
    p.add_argument("--site-url", help="ポートフォリオサイトの URL（例 https://portfolio.example.com）")
    p.add_argument("--backend-url",
                   help="フロントエンドから呼ぶバックエンドの URL（https のみ。apps.json の env に書く）")
    p.add_argument("--build-image", action="store_true",
                   help="docker でバックエンドのイメージを作成する（ベースイメージを外部から取得する）")
    return p


def _rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


_BACKEND_URL_UNUSED = "配信登録できるフロントエンドがないため、--backend-url は使いませんでした"


def _frontend_env(names: list[str], backend_url: str | None) -> tuple[dict[str, str], list[str]]:
    """--backend-url を apps.json の env に書く内容と警告を返す。names はフロントエンドの環境変数名の候補（順位順）。"""
    if backend_url is None:
        return {}, []
    if not names:
        return {}, ["--backend-url を書く環境変数名（VITE_・PUBLIC_・NEXT_PUBLIC_ で始まり API・BACKEND・SERVER と URL などを"
                    "含む名前）がフロントエンドに見つからないため、apps.json の env に手で書いてください"]
    warnings = [f"--backend-url の書き先に {names[0]} を選びました。ほかの候補（{', '.join(names[1:])}）が正しければ"
                " apps.json の env を直してください"] if len(names) > 1 else []
    return {names[0]: backend_url}, warnings


def _suggest_backend_url(names: list[str], env: dict[str, str]) -> list[str]:
    """--backend-url なしで、候補の名前がどれも env にないときに書き方を案内する。"""
    if not names or any(n in env for n in names):
        return []
    return [f"フロントエンドが {', '.join(names)} を参照しています。バックエンドの URL は --backend-url を付けて"
            f'再実行するか、apps.json の env に {{"{names[0]}": "https://..."}} を書くと反映されます']


def _backend_env(backend_dir: Path, site_url: str | None, slug: str, registered: bool,
                 skip_dirs: list[Path]) -> tuple[dict[str, str], list[str]]:
    """Dockerfile の ENV に書くフロントエンドの URL と警告を返す。"""
    if site_url is None:
        return {}, ["サイトの URL（--site-url または portfolio-site/infra/parameters.json の DomainName）を判定できないため、"
                    "Dockerfile にフロントエンドの URL を書きませんでした"]
    warnings: list[str] = []
    names = find_backend_env_names(backend_dir, skip_dirs=skip_dirs)
    if not names:
        names = ["FRONTEND_URL"]
        warnings.append("バックエンドがフロントエンドの URL を読む環境変数を判定できないため、FRONTEND_URL として"
                        "Dockerfile に書きました。バックエンドが読む名前に合わせてください")
    env = frontend_url_env(names, site_url, slug, registered)
    if not env:
        warnings.append("サイトの URL に Dockerfile に書けない文字が含まれるため、フロントエンドの URL を書きませんでした")
    with_path = [n for n, v in env.items() if urlsplit(v).path not in ("", "/")]
    if with_path:
        warnings.append(f"{', '.join(with_path)} にはアプリの URL（パス付き）を書きました。CORS の許可オリジンに使う変数なら、"
                        "オリジン（パスなし）に直してください")
    return env, warnings


def run_import(args: argparse.Namespace, repo_root: Path, run, today: date) -> dict:
    if args.site_url is not None and not _SITE_URL.fullmatch(args.site_url):
        raise PortfolioError("--site-url は http:// または https:// で始まる URL にしてください")
    if args.backend_url is not None and not HTTPS_URL.fullmatch(args.backend_url):
        raise PortfolioError("--backend-url は https:// で始まる URL（英数字と . - _ ~ / だけ、クエリなし）にしてください")
    # サイトの URL は明示指定を優先し、なければスタックのパラメーター（DomainName）から作る
    site_url = args.site_url or read_site_url(repo_root)
    target = resolve_target(Path(args.source), repo_root, args.slug)
    warnings: list[str] = []
    if args.site_url is None and site_url is not None:
        warnings.append(f"サイトの URL を portfolio-site/infra/parameters.json の DomainName から {site_url} としました")
    if target.copy_from is not None:
        copy_tree(target.copy_from, target.project_dir)
    project = target.project_dir

    frontend = detect_frontend(project, target.slug, require_lockfile=True)
    backend = detect_backend(project, frontend)
    frontend_out = None
    registered = False
    deliverable = frontend is not None and frontend.kind is not None
    if args.backend_url is not None and not deliverable:
        warnings.append(_BACKEND_URL_UNUSED)
    if frontend is not None:
        # ルートにフロントエンドがある場合に、バックエンドまで apps/ にコピーしないようにする
        exclude = [backend.dir] if backend is not None and frontend.dir in backend.dir.parents else []
        names = find_frontend_env_names(frontend.dir, skip_dirs=exclude) if deliverable else []
        env, w = _frontend_env(names, args.backend_url if deliverable else None)
        warnings += w
        registered, w, env = register_frontend(frontend, target.slug, repo_root, project, exclude=exclude, env=env)
        warnings += w
        if args.backend_url is None:
            warnings += _suggest_backend_url(names, env)
        if registered and backend is not None and backend.dir == frontend.dir:
            warnings.append("フロントエンドとバックエンドが同じディレクトリにあるため、portfolio-site/apps/ にバックエンドの"
                            "ファイルも含まれています。不要なファイルは apps/ から削除してください")
        frontend_out = {"dir": _rel(frontend.dir, repo_root), "kind": frontend.kind, "registered": registered,
                        "env": env}

    backend_out = None
    if backend is not None:
        # バックエンド内にあるフロントエンドの .env.example などを、バックエンドの変数として拾わない
        nested = [frontend.dir] if frontend is not None and backend.dir in frontend.dir.parents else []
        env, w = _backend_env(backend.dir, site_url, target.slug, registered, nested)
        warnings += w
        docker = write_docker_files(backend, env)
        warnings += docker.warnings
        image = None
        if args.build_image and docker.has_cmd:
            image = _rel(build_image(backend.dir, target.slug, repo_root, run=run), repo_root)
        backend_out = {"dir": _rel(backend.dir, repo_root), "kind": backend.kind,
                       "dockerfile": _rel(docker.dockerfile, repo_root), "image": image, "env": env}

    tags: list[str] = []
    for t in (frontend.tags if frontend else []) + (backend.tags if backend else []) + (["Docker"] if backend else []):
        if t not in tags:
            tags.append(t)
    app_url = f"{site_url.rstrip('/')}/apps/{target.slug}/" if site_url and registered else None
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
