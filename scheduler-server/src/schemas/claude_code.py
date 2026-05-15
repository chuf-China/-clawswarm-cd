"""Claude Code 实例与连接测试相关 schema。"""

from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.common import OrmModel, TimestampedModel


class ClaudeCodeInstanceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=120)
    role_name: str | None = Field(default=None, max_length=120)
    workspace_dir: str = Field(min_length=1, max_length=500)
    allowed_tools: list[str] | None = Field(default=None)
    model_override: str | None = Field(default=None, max_length=120)
    system_prompt: str | None = Field(default=None)
    status: str = Field(default="active", pattern="^(active|disabled|offline)$")


class ClaudeCodeInstanceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role_name: str | None = Field(default=None, max_length=120)
    workspace_dir: str | None = Field(default=None, min_length=1, max_length=500)
    allowed_tools: list[str] | None = Field(default=None)
    model_override: str | None = Field(default=None, max_length=120)
    system_prompt: str | None = Field(default=None)
    status: str | None = Field(default=None, pattern="^(active|disabled|offline)$")


class ClaudeCodeInstanceRead(TimestampedModel):
    id: int
    instance_key: str
    runtime_target_id: int
    name: str
    cs_id: str
    display_name: str
    role_name: str | None
    workspace_dir: str
    allowed_tools: list[str] | None = None
    model_override: str | None
    system_prompt: str | None
    status: str
    tools_configured: bool = False


class ClaudeCodeConnectionTestRead(BaseModel):
    ok: bool
    version: str | None = None
    detail: str | None = None


class ClaudeCodeInstanceListRead(OrmModel):
    """不带时间戳的简要列表返回，便于前端展示。"""
    id: int
    instance_key: str
    name: str
    display_name: str
    role_name: str | None
    workspace_dir: str
    status: str
