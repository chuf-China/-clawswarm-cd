"""
这个文件负责前端左侧通讯录所需的聚合接口。

主要职责：
1. 一次性返回实例树、实例下的 agent、Runtime Target（Claude Code / Hermes）以及群组列表。
2. 把多张表的数据整理成前端可以直接渲染的树形结构。
3. 减少前端首次加载时的接口调用次数。
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.models.agent_profile import AgentProfile
from src.models.chat_group import ChatGroup
from src.models.chat_group_member import ChatGroupMember
from src.models.claude_code_instance import ClaudeCodeInstance
from src.models.hermes_instance import HermesInstance
from src.models.openclaw_instance import OpenClawInstance
from src.models.runtime_target import RuntimeTarget
from src.schemas.address_book import (
    AddressBookAgent,
    AddressBookGroup,
    AddressBookGroupMember,
    AddressBookInstance,
    AddressBookResponse,
    AddressBookRuntimeTarget,
)
from src.services.agent_cs_id import ensure_agent_cs_id

router = APIRouter(prefix="/api", tags=["address-book"])


@router.get("/address-book", response_model=AddressBookResponse)
def get_address_book(db: Session = Depends(db_session)) -> AddressBookResponse:
    instances = list(
        db.scalars(
            select(OpenClawInstance)
            .where(OpenClawInstance.status != "disabled")
            .order_by(OpenClawInstance.id)
        )
    )
    visible_instance_ids = {instance.id for instance in instances}
    agents = list(
        db.scalars(
            select(AgentProfile)
            .where(
                AgentProfile.removed_from_openclaw.is_(False),
                AgentProfile.instance_id.in_(visible_instance_ids) if visible_instance_ids else False,
            )
            .order_by(AgentProfile.instance_id, AgentProfile.id)
        )
    )
    groups = list(db.scalars(select(ChatGroup).order_by(ChatGroup.id)))
    members = list(db.scalars(select(ChatGroupMember).order_by(ChatGroupMember.group_id, ChatGroupMember.id)))

    # Runtime Targets: Claude Code / Hermes 等非 OpenClaw 可寻址目标
    runtime_targets = list(
        db.scalars(
            select(RuntimeTarget)
            .where(RuntimeTarget.runtime_type.in_(["claude-code", "hermes"]))
            .order_by(RuntimeTarget.id)
        )
    )

    agent_map = {agent.id: agent for agent in agents}
    instance_map = {instance.id: instance for instance in instances}
    runtime_target_map = {rt.id: rt for rt in runtime_targets}

    # Preload instance names for runtime targets
    cc_instances = {inst.id: inst for inst in list(db.scalars(select(ClaudeCodeInstance)))}
    hermes_instances = {inst.id: inst for inst in list(db.scalars(select(HermesInstance)))}

    def _rt_instance_name(rt: RuntimeTarget) -> str | None:
        if rt.runtime_type == "claude-code":
            inst = cc_instances.get(rt.runtime_instance_id)
            return inst.display_name if inst else None
        if rt.runtime_type == "hermes":
            inst = hermes_instances.get(rt.runtime_instance_id)
            return inst.display_name if inst else None
        return None

    grouped_agents: dict[int, list[AddressBookAgent]] = {}
    touched = False
    for agent in agents:
        if not (agent.cs_id or "").strip():
            ensure_agent_cs_id(agent)
            touched = True
        grouped_agents.setdefault(agent.instance_id, []).append(
            AddressBookAgent(
                id=agent.id,
                agent_key=agent.agent_key,
                cs_id=agent.cs_id or "",
                display_name=agent.display_name,
                role_name=agent.role_name,
                enabled=agent.enabled,
            )
        )
    if touched:
        db.commit()

    group_members: dict[int, list[AddressBookGroupMember]] = {}
    for member in members:
        if member.runtime_target_id is not None:
            target = runtime_target_map.get(member.runtime_target_id)
            if not target:
                continue
            group_members.setdefault(member.group_id, []).append(
                AddressBookGroupMember(
                    id=member.id,
                    runtime_target_id=member.runtime_target_id,
                    display_name=target.display_name or target.target_key,
                    instance_name=_rt_instance_name(target),
                    runtime_type=target.runtime_type,
                    cs_id=target.cs_id,
                )
            )
        elif member.instance_id is not None and member.agent_id is not None:
            agent = agent_map.get(member.agent_id)
            instance = instance_map.get(member.instance_id)
            if not agent or not instance:
                continue
            group_members.setdefault(member.group_id, []).append(
                AddressBookGroupMember(
                    id=member.id,
                    instance_id=member.instance_id,
                    agent_id=member.agent_id,
                    display_name=agent.display_name,
                    agent_key=agent.agent_key,
                    instance_name=instance.name,
                    cs_id=agent.cs_id or "",
                )
            )

    return AddressBookResponse(
        instances=[
            AddressBookInstance(id=i.id, name=i.name, status=i.status, agents=grouped_agents.get(i.id, []))
            for i in instances
        ],
        runtime_targets=[
            AddressBookRuntimeTarget(
                id=rt.id,
                runtime_type=rt.runtime_type,
                display_name=rt.display_name or rt.target_key,
                role_name=rt.role_name,
                cs_id=rt.cs_id or "",
                instance_name=_rt_instance_name(rt) or rt.display_name or rt.target_key,
                enabled=rt.enabled,
            )
            for rt in runtime_targets
        ],
        groups=[
            AddressBookGroup(id=g.id, name=g.name, description=g.description, members=group_members.get(g.id, []))
            for g in groups
        ],
    )
