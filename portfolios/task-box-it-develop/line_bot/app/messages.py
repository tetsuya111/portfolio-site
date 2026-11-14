"""依頼者向けの文言。専門用語を使わず、短くする。文言はここに集約する。"""

NOT_CONTRACTED = "対話は受け付けておりません。下のボタンからお選びください。"
NEED_REGISTRATION = "はじめに、お名前とメールアドレスの登録をお願いします。"
WAITING = "しばらくお待ちください。"
LLM_FAILED = "エラーになりました。少し待ってから、もう一度送ってください。"
LIMIT_REACHED = "今日はたくさんお話ししたので、ここまでにさせてください。明日になるとまた使えます。"
UNDER_CONSTRUCTION = "機能改修中です。準備ができましたらお知らせします。"
REGISTERED = "登録完了しました。ありがとうございます。"
DIALOGUE_PLACEHOLDER = "メッセージを受け取りました。担当者が確認しますので、少々お待ちください。"

REGISTER_FORMAT = "【ユーザー情報の登録】\n名前: <名前>\nメールアドレス: <メールアドレス>"
REGISTER_EXAMPLE = "【ユーザー情報の登録】\n名前: 山田太郎\nメールアドレス: taro@example.com"


def register_guide(liff_url: str = "") -> str:
    if liff_url:
        return f"下のページからご登録ください。\n{liff_url}"
    return "次の形式でメッセージを送ってください。\n\n" + REGISTER_EXAMPLE


def format_error(reason: str) -> str:
    return f"{reason}\n\n次の形式でお送りください。\n\n{REGISTER_EXAMPLE}"


def contract_guide(url: str) -> str:
    return f"こちらのページからお手続きください。\n{url}"


def hearing_site_guide(url: str) -> str:
    return f"作りたいものの整理は、こちらのページでできます。\n{url}"


ESTIMATE_GUIDE = "お金のお話は、こちらではお答えできません。別のページでご案内します。"
