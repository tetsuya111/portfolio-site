"""users / conversation_turns / processed_events を作る

Revision ID: 0001_initial
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("line_user_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=254), nullable=False, server_default=""),
        sa.Column("contract_status", sa.String(length=20), nullable=False, server_default="none"),
        sa.Column("daily_llm_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_calls_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "conversation_turns",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "line_user_id",
            sa.String(length=64),
            sa.ForeignKey("users.line_user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_turns_user_created", "conversation_turns", ["line_user_id", "created_at"]
    )
    op.create_table(
        "processed_events",
        sa.Column("webhook_event_id", sa.String(length=64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("processed_events")
    op.drop_index("ix_turns_user_created", table_name="conversation_turns")
    op.drop_table("conversation_turns")
    op.drop_table("users")
