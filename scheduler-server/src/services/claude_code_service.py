"""Claude Code 实例管理服务。"""

from __future__ import annotations

import json
import shutil

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.claude_code_instance import ClaudeCodeInstance
from src.models.conversation import Conversation
from src.models.runtime_target import RuntimeTarget
from src.schemas.claude_code import (
    ClaudeCodeConnectionTestRead,
    ClaudeCodeInstanceCreate,
    ClaudeCodeInstanceRead,
    ClaudeCodeInstanceUpdate,
)
from src.schemas.common import dump_model
from src.services.runtime_target_service import sync_claude_code_runtime_target

DEFAULT_ALLOWED_TOOLS = ["Read", "Edit", "Bash", "WebSearch"]


def serialize_instance(instance: ClaudeCodeInstance) -> ClaudeCodeInstanceRead:
    """整理 Claude Code 实例响应，避免泄漏敏感信息。"""
    if instance.runtime_target_id is None or instance.cs_id is None:
        raise HTTPException(status_code=500, detail="Claude Code instance runtime target is missing")
    tools = None
    if instance.allowed_tools_json:
        try:
            tools = json.loads(instance.allowed_tools_json)
        except (ValueError, json.JSONDecodeError):
            tools = None
    return ClaudeCodeInstanceRead(
        id=instance.id,
        instance_key=instance.instance_key,
        runtime_target_id=instance.runtime_target_id,
        name=instance.name,
        cs_id=instance.cs_id,
        display_name=instance.display_name,
        role_name=instance.role_name,
        workspace_dir=instance.workspace_dir,
        allowed_tools=tools or DEFAULT_ALLOWED_TOOLS,
        model_override=instance.model_override,
        system_prompt=instance.system_prompt,
        status=instance.status,
        tools_configured=bool(tools) if tools else False,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


def _dump_tools(tools: list[str] | None) -> str | None:
    if not tools:
        return None
    return json.dumps(tools, ensure_ascii=False)


def list_instances(db: Session) -> list[ClaudeCodeInstanceRead]:
    items = list(db.scalars(select(ClaudeCodeInstance).order_by(ClaudeCodeInstance.id)))
    for item in items:
        sync_claude_code_runtime_target(db=db, instance=item)
    db.commit()
    return [serialize_instance(item) for item in items]


def create_instance(*, db: Session, payload: ClaudeCodeInstanceCreate) -> ClaudeCodeInstanceRead:
    data = dump_model(payload)
    data["allowed_tools_json"] = _dump_tools(data.pop("allowed_tools", None))
    item = ClaudeCodeInstance(**data)
    db.add(item)
    db.flush()
    sync_claude_code_runtime_target(db=db, instance=item)
    db.commit()
    db.refresh(item)
    return serialize_instance(item)


def update_instance(*, db: Session, instance_id: int, payload: ClaudeCodeInstanceUpdate) -> ClaudeCodeInstanceRead:
    item = db.get(ClaudeCodeInstance, instance_id)
    if not item:
        raise HTTPException(status_code=404, detail="Claude Code instance not found")

    updates = dump_model(payload, exclude_unset=True)
    if "allowed_tools" in updates:
        updates["allowed_tools_json"] = _dump_tools(updates.pop("allowed_tools", None))
    for key, value in updates.items():
        setattr(item, key, value)
    sync_claude_code_runtime_target(db=db, instance=item)
    db.commit()
    db.refresh(item)
    return serialize_instance(item)


def set_instance_enabled(*, db: Session, instance_id: int, enabled: bool) -> ClaudeCodeInstanceRead:
    item = db.get(ClaudeCodeInstance, instance_id)
    if not item:
        raise HTTPException(status_code=404, detail="Claude Code instance not found")
    item.status = "active" if enabled else "disabled"
    sync_claude_code_runtime_target(db=db, instance=item)
    db.commit()
    db.refresh(item)
    return serialize_instance(item)


def delete_instance(*, db: Session, instance_id: int) -> None:
    item = db.get(ClaudeCodeInstance, instance_id)
    if not item:
        raise HTTPException(status_code=404, detail="Claude Code instance not found")
    if item.runtime_target_id:
        target = db.get(RuntimeTarget, item.runtime_target_id)
        if target:
            db.delete(target)
    db.delete(item)
    db.commit()


def test_instance(*, db: Session, instance_id: int) -> ClaudeCodeConnectionTestRead:
    item = db.get(ClaudeCodeInstance, instance_id)
    if not item:
        raise HTTPException(status_code=404, detail="Claude Code instance not found")

    claude_path = shutil.which("claude")
    if not claude_path:
        return ClaudeCodeConnectionTestRead(ok=False, version=None, detail="claude command not found in PATH")

    import subprocess
    try:
        result = subprocess.run(
            [claude_path, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip() or "unknown"
            return ClaudeCodeConnectionTestRead(ok=True, version=version)
        return ClaudeCodeConnectionTestRead(ok=False, version=None, detail=result.stderr.strip())
    except subprocess.TimeoutExpired:
        return ClaudeCodeConnectionTestRead(ok=False, version=None, detail="claude --version timed out")
    except Exception as exc:
        return ClaudeCodeConnectionTestRead(ok=False, version=None, detail=str(exc))


def create_or_get_conversation(*, db: Session, instance_id: int) -> Conversation:
    instance = db.get(ClaudeCodeInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Claude Code instance not found")
    if instance.status == "disabled":
        raise HTTPException(status_code=400, detail="Claude Code instance is disabled")
    if not instance.runtime_target_id:
        sync_claude_code_runtime_target(db=db, instance=instance)
        db.flush()
    existing = db.scalar(
        select(Conversation).where(
            Conversation.type == "direct",
            Conversation.direct_runtime_target_id == instance.runtime_target_id,
        )
    )
    if existing:
        return existing
    item = Conversation(
        type="direct",
        title=f"{instance.name} / {instance.display_name}",
        direct_runtime_target_id=instance.runtime_target_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
