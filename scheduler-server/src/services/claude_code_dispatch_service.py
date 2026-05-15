"""Claude Code 消息分发服务 — 通过 Hermes Gateway 实现。

Claude Code Runtime Target 的消息不再调用本地 claude -p 子进程，
而是走 Hermes Gateway HTTP API，从而获得完整 MCP 工具链、对话状态管理
以及与 Hermes Agent 对等的模型调用能力。
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.conversation import Conversation
from src.models.hermes_instance import HermesInstance
from src.models.message import Message
from src.models.message_dispatch import MessageDispatch
from src.models.runtime_target import RuntimeTarget
from src.services.conversation_events import conversation_event_hub

STREAM_UPDATE_INTERVAL_SECONDS = 0.3
GATEWAY_API_PATH = "/v1/responses"

# In-memory per-conversation previous_response_id tracking.
# In production this should be persisted (e.g. in MessageDispatch.channel_trace_id).
_conversation_state: dict[int, str | None] = {}


async def dispatch_direct_message(
    *,
    db: Session,
    conversation: Conversation,
    message: Message,
) -> list[str]:
    """把用户消息通过 Hermes Gateway 发送给 Claude Code Agent。"""
    target = db.get(RuntimeTarget, conversation.direct_runtime_target_id)
    if not target or target.runtime_type != "claude-code":
        raise HTTPException(status_code=400, detail="invalid Claude Code conversation target")

    gateway = _find_gateway_instance(db)
    return await _dispatch_via_gateway(
        db=db,
        conversation=conversation,
        message=message,
        target=target,
        gateway=gateway,
        dispatch_mode="claude_code_direct",
    )


async def dispatch_group_broadcast(
    *,
    db: Session,
    conversation: Conversation,
    message: Message,
    group: Any,
    target: RuntimeTarget,
    mentions: list[str] | None = None,
) -> str | None:
    """Dispatch a group message to a Claude Code runtime target via Gateway."""
    if not target.enabled:
        return None

    gateway = _find_gateway_instance(db)
    results = await _dispatch_via_gateway(
        db=db,
        conversation=conversation,
        message=message,
        target=target,
        gateway=gateway,
        dispatch_mode="group_mention" if mentions else "group_broadcast",
    )
    return results[0] if results else None


async def dispatch_agent_dialogue_turn(
    *,
    db: Session,
    conversation: Conversation,
    message: Message,
    target: RuntimeTarget,
    sender_label: str,
    dispatch_mode: str,
) -> str | None:
    """Dispatch an agent dialogue turn to a Claude Code target via Gateway."""
    if not target.enabled:
        return None

    gateway = _find_gateway_instance(db)
    results = await _dispatch_via_gateway(
        db=db,
        conversation=conversation,
        message=message,
        target=target,
        gateway=gateway,
        dispatch_mode=dispatch_mode,
    )
    return results[0] if results else None


async def run_direct_dispatch(
    *,
    session_local,
    conversation_id: int,
    message_id: str,
) -> None:
    """在独立 Session 中执行 Claude Code 分发。"""
    with session_local() as db:
        conversation = db.get(Conversation, conversation_id)
        message = db.get(Message, message_id)
        if not conversation or not message:
            return
        try:
            await dispatch_direct_message(db=db, conversation=conversation, message=message)
        except HTTPException:
            pass
        finally:
            await _publish_update(conversation_id, message_id)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

_GATEWAY_CACHE: tuple[float, int, HermesInstance] | None = None  # (timestamp, id, instance)


def _find_gateway_instance(db: Session) -> HermesInstance:
    """Find the first active HermesInstance pointing to the local Gateway (30s cache)."""
    global _GATEWAY_CACHE
    now = time.monotonic()
    if _GATEWAY_CACHE is not None:
        ts, _id, inst = _GATEWAY_CACHE
        if now - ts < 30:
            return inst
    inst = db.scalar(
        select(HermesInstance).where(HermesInstance.status == "active").limit(1)
    )
    if not inst:
        raise HTTPException(status_code=503, detail="no active Hermes Gateway instance")
    _GATEWAY_CACHE = (now, inst.id, inst)
    return inst


async def _dispatch_via_gateway(
    *,
    db: Session,
    conversation: Conversation,
    message: Message,
    target: RuntimeTarget,
    gateway: HermesInstance,
    dispatch_mode: str,
) -> list[str]:
    """Create dispatch + reply_message and stream from Gateway."""
    dispatch = MessageDispatch(
        id=f"dsp_{uuid.uuid4().hex[:24]}",
        message_id=message.id,
        conversation_id=conversation.id,
        runtime_target_id=target.id,
        dispatch_mode=dispatch_mode,
        channel_message_id=message.id,
        status="pending",
    )
    db.add(dispatch)
    db.flush()

    reply_message = Message(
        id=f"msg_cc_{dispatch.id}",
        conversation_id=conversation.id,
        sender_type="agent",
        sender_label=target.display_name,
        sender_cs_id=target.cs_id,
        content="",
        status="pending",
    )
    db.add(reply_message)
    db.commit()
    await _publish_update(conversation.id, reply_message.id)

    # Build input text: resolve attachment paths, prepend system prompt
    input_text = _build_input_text(db=db, message=message, target=target, conversation_id=conversation.id)

    # Build Gateway payload
    payload: dict[str, Any] = {
        "model": (gateway.default_model or gateway.instance_key).strip(),
        "input": input_text,
    }
    prev_id = _conversation_state.get(conversation.id)
    if prev_id:
        payload["previous_response_id"] = prev_id

    dispatch.status = "streaming"
    db.commit()

    try:
        reply_text, response_id = await asyncio.wait_for(
            _stream_from_gateway(
                db=db,
                gateway=gateway,
                payload=payload,
                conversation_id=conversation.id,
                reply_message=reply_message,
            ),
            timeout=300.0,
        )
    except asyncio.TimeoutError:
        _mark_failed(db=db, dispatch=dispatch, message=message, reply_message=reply_message, error="Gateway dispatch timed out (300s)")
        raise HTTPException(status_code=504, detail="Gateway timed out")
    except httpx.TimeoutException:
        _mark_failed(db=db, dispatch=dispatch, message=message, reply_message=reply_message, error="Gateway timed out")
        raise HTTPException(status_code=504, detail="Gateway timed out")
    except (httpx.ConnectError, httpx.NetworkError) as exc:
        _mark_failed(db=db, dispatch=dispatch, message=message, reply_message=reply_message, error=f"Gateway unreachable: {exc}")
        raise HTTPException(status_code=503, detail="Gateway unreachable")
    except httpx.HTTPStatusError as exc:
        _mark_failed(db=db, dispatch=dispatch, message=message, reply_message=reply_message, error=f"Gateway HTTP {exc.response.status_code}")
        raise HTTPException(status_code=502, detail="Gateway request failed")
    except Exception as exc:
        _mark_failed(db=db, dispatch=dispatch, message=message, reply_message=reply_message, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Gateway execution failed: {exc}")

    reply_message.content = reply_text
    reply_message.status = "completed"
    dispatch.status = "completed"
    dispatch.channel_trace_id = response_id
    message.status = "completed"
    db.commit()

    # Track response_id for next turn
    if response_id:
        _conversation_state[conversation.id] = response_id

    return [dispatch.id]


def _build_input_text(
    *,
    db: Session,
    message: Message,
    target: RuntimeTarget,
    conversation_id: int,
) -> str:
    """Build the text to send to the Gateway, with system prompt and resolved paths."""
    parts: list[str] = []

    # Load ClaudeCodeInstance for system_prompt
    from src.models.claude_code_instance import ClaudeCodeInstance
    instance = db.get(ClaudeCodeInstance, target.runtime_instance_id)
    if instance and instance.system_prompt:
        parts.append(f"[System Instruction]\n{instance.system_prompt}\n")
    if instance and instance.role_name:
        parts.append(f"[Your Role]\nYou are {instance.role_name}.\n")

    # Load recent conversation history
    recent = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.status == "completed")
            .order_by(Message.created_at.desc())
            .limit(20)
        )
    )
    recent.reverse()
    if recent:
        parts.append("[Conversation History]")
        for msg in recent[:-1]:
            sender = msg.sender_label or msg.sender_type or "unknown"
            parts.append(f"{sender}: {msg.content[:2000]}")

    # Current message with resolved attachment paths
    content = message.content
    content = _resolve_attachment_paths(content)

    if recent:
        parts.append("")
    parts.append("[Current Message]")
    parts.append(content)
    parts.append("")
    parts.append("You have full access to MCP tools: files, terminal, web search, and more. Use them as needed.")

    return "\n".join(parts)


def _resolve_attachment_paths(text: str) -> str:
    """Replace /uploads/xxx attachment URLs with absolute filesystem paths."""
    def _replace(m: re.Match) -> str:
        url = m.group(3)
        if url.startswith("/uploads/"):
            # Compute absolute path: scheduler-server/uploads/xxx
            from pathlib import Path
            abs_path = str(Path(__file__).resolve().parents[3] / "uploads" / url.removeprefix("/uploads/"))
            return f"[[attachment:{m.group(1)}|{m.group(2)}|{abs_path}]]"
        return m.group(0)

    return re.sub(r"\[\[attachment:([^|\]]+)\|([^|\]]*)\|([^\]]+)\]\]", _replace, text)


async def _stream_from_gateway(
    *,
    db: Session,
    gateway: HermesInstance,
    payload: dict[str, Any],
    conversation_id: int,
    reply_message: Message,
) -> tuple[str, str | None]:
    """Stream response from Hermes Gateway SSE endpoint."""
    url = gateway.api_base_url.rstrip("/") + GATEWAY_API_PATH
    headers = {"content-type": "application/json; charset=utf-8"}
    api_key = (gateway.api_key or "").strip()
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"

    payload["stream"] = True

    chunks: list[str] = []
    response_id: str | None = None
    last_flush_at = 0.0

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()

            event_type: str | None = None
            data_lines: list[str] = []

            async for line in response.aiter_lines():
                if line == "":
                    event = _decode_sse_event(event_type=event_type, data_lines=data_lines)
                    event_type = None
                    data_lines = []
                    if event is None:
                        continue

                    # Extract response_id
                    etype = str(event.get("type") or event.get("event") or "").strip()
                    if etype in {"response.created", "response.completed"}:
                        resp = event.get("response") if isinstance(event.get("response"), dict) else event
                        if isinstance(resp, dict):
                            rid = resp.get("id")
                            if isinstance(rid, str) and rid.strip():
                                response_id = rid

                    # Extract text delta
                    delta = _extract_delta(event)
                    if delta:
                        chunks.append(delta)
                        now = time.monotonic()
                        if now - last_flush_at >= STREAM_UPDATE_INTERVAL_SECONDS:
                            reply_message.content = "".join(chunks)
                            reply_message.status = "pending"
                            db.commit()
                            await _publish_update(conversation_id, reply_message.id)
                            last_flush_at = now
                    continue

                if line.startswith("event:"):
                    event_type = line.removeprefix("event:").strip()
                elif line.startswith("data:"):
                    data_lines.append(line.removeprefix("data:").strip())

            # Last event
            event = _decode_sse_event(event_type=event_type, data_lines=data_lines)
            if event:
                etype = str(event.get("type") or event.get("event") or "").strip()
                if etype in {"response.created", "response.completed"}:
                    resp = event.get("response") if isinstance(event.get("response"), dict) else event
                    if isinstance(resp, dict):
                        rid = resp.get("id")
                        if isinstance(rid, str) and rid.strip():
                            response_id = rid
                delta = _extract_delta(event)
                if delta:
                    chunks.append(delta)

    reply_text = "".join(chunks).strip()
    if not reply_text:
        raise ValueError("Gateway response is empty")
    reply_message.content = reply_text
    db.commit()
    await _publish_update(conversation_id, reply_message.id)
    return reply_text, response_id


def _decode_sse_event(*, event_type: str | None, data_lines: list[str]) -> dict[str, Any] | None:
    if not data_lines:
        return None
    data = "\n".join(data_lines).strip()
    if not data or data == "[DONE]":
        return None
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and event_type and "type" not in payload:
        payload["type"] = event_type
    return payload


def _extract_delta(event: dict[str, Any]) -> str:
    delta = event.get("delta")
    if isinstance(delta, str):
        return delta
    if isinstance(delta, dict):
        text = delta.get("text") or delta.get("content")
        if isinstance(text, str):
            return text
    text = event.get("text")
    if isinstance(text, str):
        return text
    return ""


def _mark_failed(
    *,
    db: Session,
    dispatch: MessageDispatch,
    message: Message,
    reply_message: Message | None = None,
    error: str,
) -> None:
    dispatch.status = "failed"
    dispatch.error_message = error[:500]
    message.status = "failed"
    if reply_message is not None:
        reply_message.status = "failed"
    db.commit()


async def _publish_update(conversation_id: int, message_id: str) -> None:
    await conversation_event_hub.publish_update(
        conversation_id,
        {"source": "claude_code_stream", "messageId": message_id},
    )
