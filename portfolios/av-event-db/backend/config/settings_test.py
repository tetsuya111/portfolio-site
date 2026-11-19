"""テスト用の設定。APP_ENV=test にしてから通常の設定を読み込む。"""

import os

os.environ["APP_ENV"] = "test"

from .settings import *  # noqa: E402, F403
