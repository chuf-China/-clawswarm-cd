/**
 * 通讯录接口的原始响应类型。
 *
 * 这一层保持与后端字段一致。
 */
export interface AddressBookAgentResponse {
    id: number;
    agent_key: string;
    cs_id: string;
    display_name: string;
    role_name: string | null;
    enabled: boolean;
}

export interface AddressBookInstanceResponse {
    id: number;
    name: string;
    status: string;
    agents: AddressBookAgentResponse[];
}

export interface AddressBookRuntimeTargetResponse {
    id: number;
    runtime_type: string;
    display_name: string;
    role_name: string | null;
    cs_id: string;
    instance_name: string;
    enabled: boolean;
}

export interface AddressBookGroupMemberResponse {
    id: number;
    instance_id: number | null;
    agent_id: number | null;
    runtime_target_id: number | null;
    display_name: string;
    agent_key: string | null;
    instance_name: string | null;
    runtime_type: string | null;
    cs_id: string | null;
}

export interface AddressBookGroupResponse {
    id: number;
    name: string;
    description: string | null;
    members: AddressBookGroupMemberResponse[];
}

export interface AddressBookResponse {
    instances: AddressBookInstanceResponse[];
    runtime_targets: AddressBookRuntimeTargetResponse[];
    groups: AddressBookGroupResponse[];
}
