"""フロントエンドを portfolio-site/apps/<スラッグ>/ にコピーし、配信の管理ファイル apps.json に登録する。"""

from __future__ import annotations

import json
from pathlib import Path

from importer import PortfolioError
from importer.copier import copy_tree
from importer.detect import Frontend
from importer.mock import Route, write_mock_handlers


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


def register_frontend(frontend: Frontend, slug: str, repo_root: Path, project: Path,
                      exclude: list[Path] | None = None,
                      mock_routes: list[Route] | None = None) -> tuple[bool, list[str], Path | None]:
    """配信登録したか（既に登録済みも True）、警告、モックの handlers.js のパス（作らなければ None）を返す。

    exclude（バックエンドのディレクトリなど）は apps/ へのコピーから除く。
    mock_routes（バックエンドのルート）を渡すと apps/<スラッグ>/mock/handlers.js の雛形を作り、新しく追加する項目に
    "mock": true（ビルド時にモックを差し込む）を入れる。handlers.js がないのに mock: true が残るとサイト全体の
    ビルドが止まるため、雛形を書いてから apps.json を更新する。
    """
    if frontend.kind is None:
        return False, [f"フロントエンドを配信登録しませんでした: {frontend.reason}"], None
    mock = mock_routes is not None
    warnings: list[str] = []
    apps = apps_dir(repo_root)
    manifest_path = apps / "apps.json"
    manifest = _load_manifest(manifest_path)  # コピー前に検証し、不正なら何も変更しない

    dest = apps / slug
    if dest.exists():
        warnings.append(f"portfolio-site/apps/{slug} が既にあるため、フロントエンドをコピーしませんでした")
    else:
        copy_tree(frontend.dir, dest, root=project, exclude=exclude)

    mock_path = None
    if mock_routes is not None:
        mock_path, w = write_mock_handlers(dest, mock_routes)
        warnings += w
        # 既にあった handlers.js がこのモックの書式でなければ（アプリ自身の MSW のモックなど）、差し込むと壊れるため使わない
        if "portfolioMock" not in mock_path.read_text(encoding="utf-8", errors="replace"):
            warnings.append("mock/handlers.js が portfolioMock の書式ではないため、モックを接続しませんでした。"
                            '書き直してから apps.json の項目に "mock": true を追加してください')
            mock, mock_path = False, None

    existing = next((a for a in manifest["apps"] if isinstance(a, dict) and a.get("slug") == slug), None)
    if existing is not None:
        warnings.append(f"apps.json に {slug} が既に登録されているため、登録内容を変更しませんでした")
        if mock and existing.get("mock") is not True:
            warnings.append(f'モックを使うには apps.json の {slug} の項目に "mock": true を追加してください')
    else:
        entry = {"slug": slug, "outputDir": frontend.output_dir, "buildArgs": frontend.build_args}
        if mock:
            entry["mock"] = True
        manifest["apps"].append(entry)
        apps.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8", newline="\n")
    return True, warnings, mock_path
