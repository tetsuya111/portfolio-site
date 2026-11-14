"""ポートフォリオ取り込みコマンドの入口（実装は importer/cli.py）。

使い方: python portfolios/portfolio-importer/add_portfolio.py <プロジェクトのパス> [--slug] [--site-url]
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from importer.cli import main  # noqa: E402

if __name__ == "__main__":
    # Windows でも日本語を含む JSON・メッセージを UTF-8 で出す
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    # このファイルは <リポジトリ>/portfolios/portfolio-importer/ にある
    sys.exit(main(sys.argv[1:], repo_root=HERE.parent.parent))
