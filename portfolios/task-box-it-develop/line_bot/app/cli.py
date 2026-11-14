"""運用コマンド。

    python -m app.cli purge
    python -m app.cli set_contract <userId> <none|active>

契約状態を変えられるのはこのコマンドだけ（Webhookの処理やLIFFの登録からは書き込まない）。
"""

import argparse
import logging
import sys

from .db import session_scope
from .models import ContractStatus, User
from .retention import purge


def _set_contract(line_user_id: str, status: str) -> int:
    if status not in ContractStatus.ALL:
        print(f"契約状態は {' / '.join(ContractStatus.ALL)} のいずれかです", file=sys.stderr)
        return 1
    with session_scope() as session:
        user = session.get(User, line_user_id)
        if user is None:
            print(f"{line_user_id} のユーザーが見つかりません（先に登録が必要です）", file=sys.stderr)
            return 1
        before = user.contract_status
        user.contract_status = status
        session.add(user)
    # 誰の契約状態をいつ変えたかを残す（名前・メールアドレスは出さない）
    logging.getLogger(__name__).info(
        "契約状態を変更: user=%s %s -> %s", line_user_id, before, status
    )
    print(f"{line_user_id}: {before} -> {status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("purge", help="保持期間を過ぎた会話履歴と処理済みイベントを消す")
    contract = sub.add_parser("set_contract", help="契約状態を変更する")
    contract.add_argument("line_user_id")
    contract.add_argument("status", choices=list(ContractStatus.ALL))

    args = parser.parse_args(argv)
    if args.command == "purge":
        result = purge()
        print(
            f"履歴 {result['turns']}件 / イベント {result['events']}件を消しました"
            f"（対象ユーザー {result['users']}人）"
        )
        return 0
    return _set_contract(args.line_user_id, args.status)


if __name__ == "__main__":
    raise SystemExit(main())
