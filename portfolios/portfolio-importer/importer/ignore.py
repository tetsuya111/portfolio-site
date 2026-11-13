"""コピー対象から除くファイルの判定（.gitignore 互換の簡易実装と、常に除くファイル）。"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# .gitignore に関係なく常に除く（非初期データ・秘密情報・VCS）
_ALWAYS_EXCLUDED_DIRS = {".git"}
_ALWAYS_EXCLUDED_FILE = re.compile(
    r"""^(?:
        .*\.(?:sqlite3?|db)(?:-(?:journal|wal|shm))?   # 非初期データ（DB）
      | \.env
      | \.env\.(?!example$).+                          # .env.example は残す
    )$""",
    re.VERBOSE,
)


def _glob_to_regex(glob: str) -> str:
    """gitignore のパターン（スラッシュ区切り）を正規表現の本体に変換する。"""
    out = []
    i = 0
    while i < len(glob):
        c = glob[i]
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("/**", i) and i + 3 == len(glob):
            out.append("/.*")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[":
            end = glob.find("]", i + 1)
            if end == -1:
                out.append(re.escape(c))
                i += 1
            else:
                body = glob[i + 1 : end]
                if body.startswith("!"):
                    body = "^" + body[1:]
                out.append("[" + body.replace("\\", "\\\\") + "]")
                i = end + 1
        elif c == "\\" and i + 1 < len(glob):
            out.append(re.escape(glob[i + 1]))
            i += 2
        else:
            out.append(re.escape(c))
            i += 1
    return "".join(out)


@dataclass(frozen=True)
class _Rule:
    base: str  # .gitignore があるディレクトリ（ルートからの相対、ルートは ""）
    regex: re.Pattern[str]
    negate: bool
    dir_only: bool


def _parse_line(line: str, base: str) -> _Rule | None:
    line = line.rstrip("\r\n")
    stripped = line.rstrip(" ")
    if not stripped or stripped.startswith("#"):
        return None
    negate = stripped.startswith("!")
    if negate:
        stripped = stripped[1:]
    dir_only = stripped.endswith("/")
    if dir_only:
        stripped = stripped.rstrip("/")
    if not stripped:
        return None
    anchored = "/" in stripped
    stripped = stripped.lstrip("/")
    body = _glob_to_regex(stripped)
    prefix = "" if anchored else "(?:.*/)?"
    return _Rule(base, re.compile(f"^{prefix}{body}$"), negate, dir_only)


class IgnoreMatcher:
    """ルートディレクトリ配下の .gitignore を読み込み、除外を判定する。"""

    def __init__(self, root: Path):
        self.root = root
        self._rules: list[_Rule] = []

    def add_gitignore(self, dir_rel: str) -> None:
        path = self.root / dir_rel / ".gitignore"
        if not path.is_file():
            return
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            rule = _parse_line(line, dir_rel)
            if rule:
                self._rules.append(rule)

    def is_excluded(self, rel_path: str, is_dir: bool) -> bool:
        name = PurePosixPath(rel_path).name
        if is_dir and name in _ALWAYS_EXCLUDED_DIRS:
            return True
        if not is_dir and _ALWAYS_EXCLUDED_FILE.match(name):
            return True
        excluded = False
        for rule in self._rules:
            if rule.dir_only and not is_dir:
                continue
            if rule.base:
                if not rel_path.startswith(rule.base + "/"):
                    continue
                target = rel_path[len(rule.base) + 1 :]
            else:
                target = rel_path
            if rule.regex.match(target):
                excluded = not rule.negate
        return excluded


def iter_files(root: Path) -> Iterator[Path]:
    """除外を適用した、root からの相対ファイルパスを返す（シンボリックリンクは返さない）。"""
    matcher = IgnoreMatcher(root)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        matcher.add_gitignore(rel_dir)

        def rel(name: str) -> str:
            return f"{rel_dir}/{name}" if rel_dir else name

        kept = []
        for d in sorted(dirnames):
            full = Path(dirpath) / d
            if full.is_symlink() or matcher.is_excluded(rel(d), True):
                continue
            kept.append(d)
        dirnames[:] = kept
        for f in sorted(filenames):
            full = Path(dirpath) / f
            if full.is_symlink() or not full.is_file():
                continue
            if matcher.is_excluded(rel(f), False):
                continue
            yield Path(rel(f))
