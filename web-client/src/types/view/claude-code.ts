import type { Camelized } from "@/utils/case";
import type {
    ClaudeCodeConnectionTestResponse,
    ClaudeCodeInstanceResponse,
} from "@/types/api/claude-code";

export type ClaudeCodeInstanceOutput = Camelized<ClaudeCodeInstanceResponse>;

export type ClaudeCodeConnectionTestOutput = Camelized<ClaudeCodeConnectionTestResponse>;

export interface ClaudeCodeInstanceInput {
    name: string;
    displayName: string;
    roleName?: string | null;
    workspaceDir: string;
    allowedTools?: string[] | null;
    modelOverride?: string | null;
    systemPrompt?: string | null;
    status?: string;
}
