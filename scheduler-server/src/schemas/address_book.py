"""
这里定义通讯录接口的响应结构。

通讯录接口会把实例、Runtime Target、以及群组视图一起返回，
方便前端左侧导航一次拿全。
"""
from pydantic import BaseModel


class AddressBookAgent(BaseModel):
    id: int
    agent_key: str
    cs_id: str
    display_name: str
    role_name: str | None
    enabled: bool


class AddressBookInstance(BaseModel):
    id: int
    name: str
    status: str
    agents: list[AddressBookAgent]


class AddressBookRuntimeTarget(BaseModel):
    id: int
    runtime_type: str
    display_name: str
    role_name: str | None
    cs_id: str
    instance_name: str
    enabled: bool


class AddressBookGroupMember(BaseModel):
    id: int
    instance_id: int | None = None
    agent_id: int | None = None
    runtime_target_id: int | None = None
    display_name: str
    agent_key: str | None = None
    instance_name: str | None = None
    runtime_type: str | None = None
    cs_id: str | None = None


class AddressBookGroup(BaseModel):
    id: int
    name: str
    description: str | None
    members: list[AddressBookGroupMember]


class AddressBookResponse(BaseModel):
    instances: list[AddressBookInstance]
    runtime_targets: list[AddressBookRuntimeTarget] = []
    groups: list[AddressBookGroup]
