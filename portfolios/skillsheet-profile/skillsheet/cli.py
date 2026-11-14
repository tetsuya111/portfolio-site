"""コマンドの本体。extract（テキスト化）と apply（profile.md の検証・置き換え）。"""

import argparse
import sys
from pathlib import Path

from skillsheet import fetch, readers
from skillsheet.errors import SkillsheetError


def _extract(source: str) -> str:
    if fetch.has_scheme(source):
        body, ext = fetch.fetch(source)
        return readers.read_bytes(body, ext)
    return readers.read_file(Path(source))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="skillsheet_profile.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p_extract = sub.add_parser("extract", help="スキルシートをテキストにして標準出力に出す")
    p_extract.add_argument("source", help="ファイルのパス、または http(s) の URL")
    args = parser.parse_args(argv)

    try:
        if args.command == "extract":
            sys.stdout.write(_extract(args.source))
            return 0
    except SkillsheetError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    return 1
