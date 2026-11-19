import os

# テストは開発用の設定で動かす（本番用の秘密鍵チェックを避ける）
os.environ.setdefault("APP_ENV", "test")
