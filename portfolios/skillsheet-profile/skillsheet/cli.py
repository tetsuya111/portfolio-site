"""コマンドの本体。extract（テキスト化）と apply（profile.md の検証・置き換え）。"""

import argparse
import json
import sys
from pathlib import Path

from skillsheet import fetch, profile, readers
from skillsheet.errors import SkillsheetError


def _extract(source: str) -> str:
    if fetch.has_scheme(source):
        body, ext = fetch.fetch(source)
        return readers.read_bytes(body, ext)
    return readers.read_file(Path(source))


def _apply(draft: str, target: Path) -> None:
    if draft == "-":
        text = sys.stdin.read()
    else:
        path = Path(draft)
        if not path.is_file():
            raise SkillsheetError(f"下書きが見つかりません: {path}")
        text = path.read_text(encoding="utf-8-sig")
    errors = profile.validate(text)
    if errors:
        raise SkillsheetError(
            "下書きが profile.md の書式に合いません（置き換えていません）\n" + "\n".join(f"- {e}" for e in errors)
        )
    if not target.parent.is_dir():
        raise SkillsheetError(f"置き換え先のディレクトリがありません: {target.parent}")
    profile.write_profile(text, target)
    print(json.dumps({"target": str(target), "replaced": True}, ensure_ascii=False))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="skillsheet_profile.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p_extract = sub.add_parser("extract", help="スキルシートをテキストにして標準出力に出す")
    p_extract.add_argument("source", help="ファイルのパス、または http(s) の URL")
    p_apply = sub.add_parser("apply", help="下書きを検証し、profile.md を置き換える")
    p_apply.add_argument("draft", help="下書きのパス。- なら標準入力から読む")
    p_apply.add_argument(
        "--target", type=Path, default=profile.DEFAULT_TARGET,
        help="置き換える profile.md（既定: portfolio-site/src/content/profile/profile.md）",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "extract":
            sys.stdout.write(_extract(args.source))
            return 0
        if args.command == "apply":
            _apply(args.draft, args.target)
            return 0
    except SkillsheetError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    return 1
