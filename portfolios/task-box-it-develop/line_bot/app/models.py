"""DBのモデル。BOTサーバー専用のDBで、Djangoのテーブルとは共有しない。"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ContractStatus:
    NONE = "none"
    ACTIVE = "active"
    ALL = (NONE, ACTIVE)


class User(Base):
    """LINEのユーザー。1アカウント1行。"""

    __tablename__ = "users"

    # 署名を検証したWebhook、または検証済みのIDトークンから得た値だけを入れる
    line_user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(254), default="")
    # 変更は管理コマンド set_contract のみ。リクエストの処理からは書き込まない
    contract_status: Mapped[str] = mapped_column(String(20), default=ContractStatus.NONE)
    daily_llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def is_contracted(self) -> bool:
        return self.contract_status == ContractStatus.ACTIVE


class ConversationTurn(Base):
    """対話の履歴。本文はログに出さない。"""

    __tablename__ = "conversation_turns"
    __table_args__ = (Index("ix_turns_user_created", "line_user_id", "created_at"),)

    # SQLite（開発用）では BIGINT が自動採番にならないため、方言ごとに型を変える
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    line_user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.line_user_id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessedEvent(Base):
    """処理済みのWebhookイベント。INSERTの主キー違反で重複を弾く。"""

    __tablename__ = "processed_events"

    webhook_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
