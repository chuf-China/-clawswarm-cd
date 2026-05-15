"""
这里定义群组和群成员管理相关的 schema。

第一阶段里，群组成员是跨实例群聊的业务基础，因此这里的响应结构会额外带展示字段。
"""
from pydantic import BaseModel, Field

from src.schemas.common import TimestampedModel


class GroupMemberAddItem(BaseModel):
    instance_id: int | None = None
    agent_id: int | None = None
    runtime_target_id: int | None = None


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    members: list[GroupMemberAddItem] = Field(default_factory=list)


class GroupRead(TimestampedModel):
    id: int
    name: str
    description: str | None


class GroupMemberAddRequest(BaseModel):
    members: list[GroupMemberAddItem]


class GroupMemberRead(BaseModel):
    id: int
    group_id: int
    instance_id: int | None = None
    agent_id: int | None = None
    runtime_target_id: int | None = None
    joined_at: str
    agent_key: str | None = None
    display_name: str
    role_name: str | None
    instance_name: str | None = None
    runtime_type: str | None = None
    cs_id: str | None = None


class GroupDetail(BaseModel):
    id: int
    name: str
    description: str | None
    members: list[GroupMemberRead]
