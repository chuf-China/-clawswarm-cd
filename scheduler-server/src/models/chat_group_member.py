"""
这个模型表示"某个群组包含的成员"。

成员可以是 OpenClaw 下的 Agent（通过 instance_id + agent_id），
也可以是 Claude Code / Hermes 等 Runtime Target（通过 runtime_target_id）。
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base


class ChatGroupMember(Base):
    __tablename__ = "chat_group_members"
    __table_args__ = (UniqueConstraint("group_id", "runtime_target_id", name="uq_group_runtime_target"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("chat_groups.id"), index=True)
    instance_id: Mapped[int | None] = mapped_column(ForeignKey("openclaw_instances.id"), nullable=True, index=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agent_profiles.id"), nullable=True, index=True)
    runtime_target_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
