"""取り込み先（portfolios/<スラッグ>）の決定とコピー。"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from importer import PortfolioError
from importer.ignore import iter_files

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# portfolios/ 直下にあるがプロジェクトではないディレクトリ
RESERVED_SLUGS = {"docs", "docker-images", "portfolio-importer"}


@dataclass(frozen=True)
class Target:
    slug: str
    project_dir: Path  # 取り込み後のプロジェクトの場所（portfolios/<スラッグ>）
    copy_from: Path | None  # コピー元。portfolios/ 配下を指定した場合は None（コピーしない）


def make_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def validate_slug(slug: str) -> None:
    if not (1 <= len(slug) <= 64) or not SLUG_RE.match(slug):
        raise PortfolioError(f"スラッグ「{slug}」は英小文字・数字をハイフンでつないだ1〜64文字にしてください")
    if slug in RESERVED_SLUGS:
        raise PortfolioError(f"スラッグ「{slug}」は予約されているため使えません")


def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def resolve_target(source: Path, repo_root: Path, slug: str | None) -> Target:
    source = source.resolve()
    repo_root = repo_root.resolve()
    portfolios = repo_root / "portfolios"
    if not source.is_dir():
        raise PortfolioError(f"ディレクトリではありません: {source}")
    if _is_within(repo_root, source):
        raise PortfolioError("リポジトリ自体（またはそれを含むディレクトリ）は指定できません")

    if portfolios in source.parents:
        name = source.relative_to(portfolios).parts[0]
        if slug is not None and slug != name:
            raise PortfolioError(f"portfolios/ 配下のプロジェクトのスラッグはディレクトリ名（{name}）から変えられません")
        validate_slug(name)
        return Target(name, portfolios / name, None)
    if _is_within(source, repo_root):
        raise PortfolioError("リポジトリ内では portfolios/ 配下のプロジェクトだけを指定できます")

    slug = slug if slug is not None else make_slug(source.name)
    validate_slug(slug)
    dest = portfolios / slug
    if dest.exists():
        raise PortfolioError(f"コピー先が既に存在します: portfolios/{slug}（上書きしません）")
    return Target(slug, dest, source)


def copy_tree(src: Path, dest: Path, root: Path | None = None, exclude: list[Path] | None = None) -> int:
    """除外規則を適用して src を dest にコピーし、コピーしたファイル数を返す。

    root（src を含むプロジェクトのルート）を渡すと、root から src までの .gitignore も適用する。
    exclude に渡したディレクトリ（src 配下のもの）はコピーしない。
    """
    count = 0
    base = root if root is not None else src
    skip = {p.relative_to(base).as_posix() for p in (exclude or []) if base in p.parents}
    files = iter_files(base, src.relative_to(base).as_posix(), skip_dirs=skip)
    for rel in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)
        count += 1
    return count
