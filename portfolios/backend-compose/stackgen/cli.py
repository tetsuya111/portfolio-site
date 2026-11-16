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
from stackgen.stack import RESERVED_SERVICES, Service, load_services, upsert_service, write_stack

# 再登録でソースを入れ直すときに残すファイル（編集した Dockerfile・VPS で置いた秘密情報）
_KEEP_ON_REFRESH = {"Dockerfile", ".dockerignore", ".env"}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="add_backend.py",
                                description="取り込んだポートフォリオのバックエンドを docker compose のフォルダに登録する")
    p.add_argument("project", help="portfolios/<スラッグ>（portfolio-importer で取り込んだプロジェクト）")
    p.add_argument("--enable-api", action="store_true",
                   help="フロントエンドを実 API に切り替える（apps.json に env を書き mock を false にする）。"
                        "VPS でバックエンドを起動してから付ける（先に切り替えると、次のデプロイでフロントエンドが壊れる）")
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
    if slug in RESERVED_SERVICES:
        raise StackError(f"スラッグ「{slug}」は compose のサービス名（リバースプロキシ）と重なるため登録できません")
    return slug, project


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _copy_backend(src: Path, dest: Path, project: Path, exclude: list[Path]) -> bool:
    """src を dest にコピーする。dest が既にあれば、残すファイル以外を新しいソースで置き換え、True を返す。

    コピーに失敗しても既存のソースを失わないよう、一時ディレクトリにコピーしてから入れ替える。
    """
    if not dest.exists():
        copy_tree(src, dest, root=project, exclude=exclude)
        return False
    staging = dest.with_name(f".{dest.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    try:
        copy_tree(src, staging, root=project, exclude=exclude)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    for child in dest.iterdir():
        # ソースに同名のファイルがあれば（取り込み元の Dockerfile など）ソースを正とする
        if child.name not in _KEEP_ON_REFRESH or (staging / child.name).exists():
            _remove(child)
    for child in staging.iterdir():
        child.rename(dest / child.name)
    staging.rmdir()
    return True


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
    # ルートにバックエンドがある場合に、配下のフロントエンドまでコピーしない
    exclude = [frontend.dir] if frontend is not None and backend.dir in frontend.dir.parents else []
    # 取り込み元のバックエンドを直したときに古いソースが VPS に上がらないよう、再登録ではソースを入れ直す
    if _copy_backend(backend.dir, dest, project, exclude):
        warnings.append(f"{_rel(dest, repo_root)} が既にあるため、ソースを入れ直しました"
                        f"（{'・'.join(sorted(_KEEP_ON_REFRESH))} は残しました）")
    dockerfile, w = write_docker_files(dest, backend.kind)
    warnings += w
    port = detect_port(dockerfile.read_text(encoding="utf-8", errors="replace"), backend.kind)

    services = upsert_service(stack_dir, Service(slug, port))
    write_stack(stack_dir, services, cfg)

    url = backend_url(cfg, slug)
    env, w = update_apps_json(repo_root, slug, url, apply=args.enable_api)
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
