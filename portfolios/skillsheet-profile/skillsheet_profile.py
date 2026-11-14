"""スキルシートから profile.md を作るためのコマンドの入口（実装は skillsheet/cli.py）。

使い方:
  python portfolios/skillsheet-profile/skillsheet_profile.py extract <ファイルのパス | URL>
  python portfolios/skillsheet-profile/skillsheet_profile.py apply <下書きのパス | -> [--target <パス>]
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from skillsheet.cli import main  # noqa: E402

if __name__ == "__main__":
    # Windows でも日本語を UTF-8 で入出力する
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
