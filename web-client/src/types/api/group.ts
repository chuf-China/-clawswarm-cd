export interface GroupResponse {
    id: number;
    name: string;
    description: string | null;
    created_at: string;
    updated_at: string;
}

export interface GroupMemberResponse {
    id: number;
    group_id: number;
    instance_id: number | null;
    agent_id: number | null;
    runtime_target_id: number | null;
    joined_at: string;
    agent_key: string | null;
    display_name: string;
    role_name: string | null;
    instance_name: string | null;
    runtime_type: string | null;
    cs_id: string | null;
}

export interface GroupDetailResponse {
    id: number;
    name: string;
    description: string | null;
    members: GroupMemberResponse[];
}
