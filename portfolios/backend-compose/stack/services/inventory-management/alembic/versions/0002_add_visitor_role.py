"""add visitor role

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-18 22:10:00

権限区分に閲覧者（visitor）を追加する。
downgrade の前に閲覧者を削除すること（残っていると制約違反で失敗する。
権限昇格を避けるため、閲覧者を自動で一般ユーザーに変える処理はしない）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_role_constraint(condition: str) -> None:
    # SQLite は制約を直接変更できないため、batch で表を作り直す。
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint("ck_users_role", condition)


def upgrade() -> None:
    _replace_role_constraint("role IN ('admin', 'staff', 'visitor')")


def downgrade() -> None:
    # 表の作り直しが途中で失敗すると一時表が残り再実行できなくなるため、先に確認する。
    visitors = (
        op.get_bind().execute(sa.text("SELECT count(*) FROM users WHERE role = 'visitor'")).scalar()
    )
    if visitors:
        raise RuntimeError(f"閲覧者が {visitors} 人残っています。削除してから戻してください。")
    _replace_role_constraint("role IN ('admin', 'staff')")
