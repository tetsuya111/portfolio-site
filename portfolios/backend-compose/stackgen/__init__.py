"""バックエンドを docker compose のフォルダ（stack/）に登録するコマンドの本体。"""


class StackError(Exception):
    """利用者に理由を伝えて終了するエラー。"""
