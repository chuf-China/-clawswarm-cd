"""Claude Code 实例管理路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.schemas.claude_code import (
    ClaudeCodeConnectionTestRead,
    ClaudeCodeInstanceCreate,
    ClaudeCodeInstanceRead,
    ClaudeCodeInstanceUpdate,
)
from src.schemas.conversation import ConversationRead
from src.services.claude_code_service import (
    create_instance,
    create_or_get_conversation,
    delete_instance,
    list_instances,
    set_instance_enabled,
    test_instance,
    update_instance,
)

router = APIRouter(prefix="/api/claude-code", tags=["claude-code"])


@router.get("/instances", response_model=list[ClaudeCodeInstanceRead])
def list_instances_endpoint(db: Session = Depends(db_session)) -> list[ClaudeCodeInstanceRead]:
    return list_instances(db)


@router.post("/instances", response_model=ClaudeCodeInstanceRead)
def create_instance_endpoint(payload: ClaudeCodeInstanceCreate, db: Session = Depends(db_session)) -> ClaudeCodeInstanceRead:
    return create_instance(db=db, payload=payload)


@router.put("/instances/{instance_id}", response_model=ClaudeCodeInstanceRead)
def update_instance_endpoint(instance_id: int, payload: ClaudeCodeInstanceUpdate, db: Session = Depends(db_session)) -> ClaudeCodeInstanceRead:
    return update_instance(db=db, instance_id=instance_id, payload=payload)


@router.delete("/instances/{instance_id}", status_code=204)
def delete_instance_endpoint(instance_id: int, db: Session = Depends(db_session)) -> None:
    delete_instance(db=db, instance_id=instance_id)


@router.post("/instances/{instance_id}/enable", response_model=ClaudeCodeInstanceRead)
def enable_instance_endpoint(instance_id: int, db: Session = Depends(db_session)) -> ClaudeCodeInstanceRead:
    return set_instance_enabled(db=db, instance_id=instance_id, enabled=True)


@router.post("/instances/{instance_id}/disable", response_model=ClaudeCodeInstanceRead)
def disable_instance_endpoint(instance_id: int, db: Session = Depends(db_session)) -> ClaudeCodeInstanceRead:
    return set_instance_enabled(db=db, instance_id=instance_id, enabled=False)


@router.post("/instances/{instance_id}/test", response_model=ClaudeCodeConnectionTestRead)
def test_instance_endpoint(instance_id: int, db: Session = Depends(db_session)) -> ClaudeCodeConnectionTestRead:
    return test_instance(db=db, instance_id=instance_id)


@router.post("/instances/{instance_id}/conversation", response_model=ConversationRead)
def open_instance_conversation(instance_id: int, db: Session = Depends(db_session)) -> ConversationRead:
    return create_or_get_conversation(db=db, instance_id=instance_id)
