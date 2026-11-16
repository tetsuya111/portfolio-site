"""コマンド本体: 設定の検証 → バックエンドの検出 → stack/services/ へのコピー → Dockerfile 生成
→ services.json・compose・nginx の更新 → apps.json の env の更新。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from importer import PortfolioError
from importer.copier import copy_tree, validate_slug
from importer.detect import detect_backend, detect_frontend
from stackgen import StackError
from stackgen.config import load_config
from stackgen.dockerfile import detect_port, write_docker_files
from stackgen.frontend_env import backend_url, load_apps_json, update_apps_json
from stackgen.stack import Service, load_services, upsert_service, write_stack

# 再登録でソースを入れ直すときに残すファイル（編集した Dockerfile・VPS で置いた秘密情報）
_KEEP_ON_REFRESH = {"Dockerfile", ".dockerignore", ".env"}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="add_backend.py",
                                description="取り込んだポートフォリオのバックエンドを docker compose のフォルダに登録する")
    p.add_argument("project", help="portfolios/<スラッグ>（portfolio-importer で取り込んだプロジェクト）")
    return p


def _rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _resolve_project(path: Path, repo_root: Path) -> tuple[str, Path]:
    project = path.resolve()
    if project.parent != repo_root / "portfolios" or not project.is_dir():
        raise StackError("portfolios/<スラッグ> のディレクトリを指定してください")
    slug = project.name
    try:  # backend-compose など、ポートフォリオでないディレクトリは予約スラッグとして拒否される
        validate_slug(slug)
    except PortfolioError as e:
        raise StackError(str(e)) from e
    return slug, project


def _clear_for_refresh(dest: Path) -> None:
    for child in dest.iterdir():
        if child.name in _KEEP_ON_REFRESH:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def run(args: argparse.Namespace, repo_root: Path, config_path: Path, stack_dir: Path) -> dict:
    cfg = load_config(config_path)  # 設定が不正なら何も書かない
    slug, project = _resolve_project(Path(args.project), repo_root)
    frontend = detect_frontend(project, slug)
    backend = detect_backend(project, frontend)
    if backend is None:
        raise StackError(f"portfolios/{slug} にバックエンド（backend/・server/・api/・ルートの Python / node）が見つかりません")
    # 不正なファイルがあれば、何かを書く前に止める（途中まで書いた状態を残さない）
    load_services(stack_dir)
    load_apps_json(repo_root)

    warnings: list[str] = []
    dest = stack_dir / "services" / slug
    if dest.exists():
        # 取り込み元のバックエンドを直したときに古いソースが VPS に上がらないよう、入れ直す
        _clear_for_refresh(dest)
        warnings.append(f"{_rel(dest, repo_root)} が既にあるため、ソースを入れ直しました"
                        f"（{'・'.join(sorted(_KEEP_ON_REFRESH))} は残しました）")
    # ルートにバックエンドがある場合に、配下のフロントエンドまでコピーしない
    exclude = [frontend.dir] if frontend is not None and backend.dir in frontend.dir.parents else []
    copy_tree(backend.dir, dest, root=project, exclude=exclude)
    dockerfile, w = write_docker_files(dest, backend.kind)
    warnings += w
    port = detect_port(dockerfile.read_text(encoding="utf-8", errors="replace"), backend.kind)

    services = upsert_service(stack_dir, Service(slug, port))
    write_stack(stack_dir, services, cfg)

    url = backend_url(cfg, slug)
    env, w = update_apps_json(repo_root, slug, url)
    warnings += w
    if not (dest / ".env").exists() and (dest / ".env.example").exists():
        warnings.append(f"バックエンドが使う環境変数は、VPS 上で stack/services/{slug}/.env に書いてください（.env.example を参照）")
    return {
        "slug": slug,
        "service": _rel(dest, repo_root),
        "port": port,
        "backendUrl": url,
        "dockerfile": _rel(dockerfile, repo_root),
        "frontendEnv": env,
        "warnings": warnings,
    }


def main(argv: list[str], repo_root: Path, config_path: Path, stack_dir: Path) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run(args, repo_root.resolve(), config_path, stack_dir.resolve())
    except (StackError, PortfolioError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
