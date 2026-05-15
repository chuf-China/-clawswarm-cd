export interface ClaudeCodeInstanceResponse {
    id: number;
    instance_key: string;
    runtime_target_id: number;
    cs_id: string;
    name: string;
    display_name: string;
    role_name: string | null;
    workspace_dir: string;
    allowed_tools: string[] | null;
    model_override: string | null;
    system_prompt: string | null;
    status: string;
    tools_configured: boolean;
    created_at: string;
    updated_at: string;
}

export interface ClaudeCodeConnectionTestResponse {
    ok: boolean;
    version: string | null;
    detail: string | null;
}
