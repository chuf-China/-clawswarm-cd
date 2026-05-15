import { apiClient } from "@/api/client";
import type {
    ClaudeCodeConnectionTestResponse,
    ClaudeCodeInstanceResponse,
} from "@/types/api/claude-code";
import type {
    ClaudeCodeConnectionTestOutput,
    ClaudeCodeInstanceInput,
    ClaudeCodeInstanceOutput,
} from "@/types/view/claude-code";
import type { ConversationResponse } from "@/types/api/conversation";
import type { ConversationOutput } from "@/types/view/conversation";
import { camelizeKeys, snakeizeKeys } from "@/utils/case";

export async function fetchClaudeCodeInstances(): Promise<ClaudeCodeInstanceOutput[]> {
    const response = await apiClient.get<ClaudeCodeInstanceResponse[]>("/api/claude-code/instances");
    return response.data.map(camelizeKeys);
}

export async function createClaudeCodeInstance(payload: ClaudeCodeInstanceInput): Promise<ClaudeCodeInstanceOutput> {
    const response = await apiClient.post<ClaudeCodeInstanceResponse>("/api/claude-code/instances", snakeizeKeys(payload));
    return camelizeKeys(response.data);
}

export async function updateClaudeCodeInstance(instanceId: number, payload: ClaudeCodeInstanceInput): Promise<ClaudeCodeInstanceOutput> {
    const response = await apiClient.put<ClaudeCodeInstanceResponse>(`/api/claude-code/instances/${instanceId}`, snakeizeKeys(payload));
    return camelizeKeys(response.data);
}

export async function deleteClaudeCodeInstance(instanceId: number): Promise<void> {
    await apiClient.delete(`/api/claude-code/instances/${instanceId}`);
}

export async function enableClaudeCodeInstance(instanceId: number): Promise<ClaudeCodeInstanceOutput> {
    const response = await apiClient.post<ClaudeCodeInstanceResponse>(`/api/claude-code/instances/${instanceId}/enable`);
    return camelizeKeys(response.data);
}

export async function disableClaudeCodeInstance(instanceId: number): Promise<ClaudeCodeInstanceOutput> {
    const response = await apiClient.post<ClaudeCodeInstanceResponse>(`/api/claude-code/instances/${instanceId}/disable`);
    return camelizeKeys(response.data);
}

export async function testClaudeCodeInstance(instanceId: number): Promise<ClaudeCodeConnectionTestOutput> {
    const response = await apiClient.post<ClaudeCodeConnectionTestResponse>(`/api/claude-code/instances/${instanceId}/test`, undefined, {
        timeout: 30000,
    });
    return camelizeKeys(response.data);
}

export async function openClaudeCodeInstanceConversation(instanceId: number): Promise<ConversationOutput> {
    const response = await apiClient.post<ConversationResponse>(`/api/claude-code/instances/${instanceId}/conversation`);
    return camelizeKeys(response.data);
}
