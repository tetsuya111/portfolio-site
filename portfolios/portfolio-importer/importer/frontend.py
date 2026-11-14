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


def _write_manifest(apps: Path, manifest_path: Path, manifest: dict) -> None:
    apps.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _merge_env(entry: dict, env: dict[str, str], slug: str) -> tuple[bool, list[str]]:
    """登録済みの項目の env に未設定の名前だけを追加する。変更したかと警告を返す。"""
    current = entry.get("env", {})
    if not isinstance(current, dict):
        return False, [f"apps.json の {slug} の env がオブジェクトでないため、env を変更しませんでした"]
    warnings: list[str] = []
    changed = False
    for name, value in env.items():
        if name not in current:
            current[name] = value
            changed = True
        elif current[name] != value:
            warnings.append(f"apps.json の {slug} の env.{name} に別の値が設定済みのため、変更しませんでした")
    if changed:
        entry["env"] = current
    return changed, warnings


def register_frontend(frontend: Frontend, slug: str, repo_root: Path, project: Path,
                      exclude: list[Path] | None = None,
                      env: dict[str, str] | None = None) -> tuple[bool, list[str], dict[str, str]]:
    """配信登録したか（既に登録済みも True）と、警告と、登録後の apps.json 上の env を返す。

    exclude（バックエンドのディレクトリなど）は apps/ へのコピーから除く。
    env（ビルド時の環境変数）は新規登録なら項目に書き、登録済みなら未設定の名前だけを追加する。
    """
    if frontend.kind is None:
        return False, [f"フロントエンドを配信登録しませんでした: {frontend.reason}"], {}
    env = env or {}
    warnings: list[str] = []
    apps = apps_dir(repo_root)
    manifest_path = apps / "apps.json"
    manifest = _load_manifest(manifest_path)  # コピー前に検証し、不正なら何も変更しない

    dest = apps / slug
    if dest.exists():
        warnings.append(f"portfolio-site/apps/{slug} が既にあるため、フロントエンドをコピーしませんでした")
    else:
        copy_tree(frontend.dir, dest, root=project, exclude=exclude)

    entry = next((a for a in manifest["apps"] if isinstance(a, dict) and a.get("slug") == slug), None)
    if entry is not None:
        warnings.append(f"apps.json に {slug} が既に登録されているため、登録内容（env 以外）を変更しませんでした")
        changed, w = _merge_env(entry, env, slug)
        warnings += w
        if changed:
            _write_manifest(apps, manifest_path, manifest)
    else:
        entry = {"slug": slug, "outputDir": frontend.output_dir, "buildArgs": frontend.build_args}
        if env:
            entry["env"] = dict(env)
        manifest["apps"].append(entry)
        _write_manifest(apps, manifest_path, manifest)
    current = entry.get("env", {})
    return True, warnings, dict(current) if isinstance(current, dict) else {}
