"""バックエンドを docker compose のフォルダ（stack/）に登録するコマンドの入口（実装は stackgen/cli.py）。

使い方: python portfolios/backend-compose/add_backend.py portfolios/<スラッグ>
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# 検出・コピーは portfolio-importer のモジュールを使う
sys.path.insert(0, str(HERE.parent / "portfolio-importer"))

from stackgen.cli import main  # noqa: E402

if __name__ == "__main__":
    # Windows でも日本語を含む JSON・メッセージを UTF-8 で出す
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    # このファイルは <リポジトリ>/portfolios/backend-compose/ にある
    sys.exit(main(sys.argv[1:], repo_root=HERE.parent.parent, config_path=HERE / "config.json",
                  stack_dir=HERE / "stack"))
