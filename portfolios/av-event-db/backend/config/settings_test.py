"""テスト用の設定。APP_ENV=test にしてから通常の設定を読み込む。"""

import os

os.environ["APP_ENV"] = "test"
# 手元の backend/.env の内容でテストが変わらないようにする
os.environ["AV_EVENT_DB_SKIP_DOTENV"] = "1"

from .settings import *  # noqa: E402, F403
