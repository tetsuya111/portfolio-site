"""フロントエンドを portfolio-site/apps/<スラッグ>/ にコピーし、配信の管理ファイル apps.json に登録する。"""

from __future__ import annotations

import json
from pathlib import Path

from importer import PortfolioError
from importer.copier import copy_tree
from importer.detect import Frontend


def apps_dir(repo_root: Path) -> Path:
    return repo_root / "portfolio-site" / "apps"


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"apps": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise PortfolioError(f"{path.name} を JSON として読めません: {e}") from e
    if not isinstance(data, dict) or not isinstance(data.get("apps"), list):
        raise PortfolioError(f'{path.name} の形式が不正です（{{"apps": [...]}} が必要です）')
    return data


def register_frontend(frontend: Frontend, slug: str, repo_root: Path, project: Path) -> tuple[bool, list[str]]:
    """配信登録したか（既に登録済みも True）と、警告を返す。"""
    if frontend.kind is None:
        return False, [f"フロントエンドを配信登録しませんでした: {frontend.reason}"]
    warnings: list[str] = []
    apps = apps_dir(repo_root)
    manifest_path = apps / "apps.json"
    manifest = _load_manifest(manifest_path)  # コピー前に検証し、不正なら何も変更しない

    dest = apps / slug
    if dest.exists():
        warnings.append(f"portfolio-site/apps/{slug} が既にあるため、フロントエンドをコピーしませんでした")
    else:
        copy_tree(frontend.dir, dest, root=project)

    if any(isinstance(a, dict) and a.get("slug") == slug for a in manifest["apps"]):
        warnings.append(f"apps.json に {slug} が既に登録されているため、登録内容を変更しませんでした")
    else:
        manifest["apps"].append({"slug": slug, "outputDir": frontend.output_dir, "buildArgs": frontend.build_args})
        apps.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8", newline="\n")
    return True, warnings
