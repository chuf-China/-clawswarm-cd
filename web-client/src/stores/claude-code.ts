import { defineStore } from "pinia";

import {
    createClaudeCodeInstance,
    deleteClaudeCodeInstance,
    disableClaudeCodeInstance,
    enableClaudeCodeInstance,
    fetchClaudeCodeInstances,
    openClaudeCodeInstanceConversation,
    testClaudeCodeInstance,
    updateClaudeCodeInstance,
} from "@/api/claude-code";
import type { ClaudeCodeInstanceInput, ClaudeCodeInstanceOutput } from "@/types/view/claude-code";

export const useClaudeCodeStore = defineStore("claudeCode", {
    state: () => ({
        instances: [] as ClaudeCodeInstanceOutput[],
        loading: false,
        savingId: null as string | null,
        creating: false,
    }),
    actions: {
        async loadInstances() {
            this.loading = true;
            try {
                this.instances = await fetchClaudeCodeInstances();
            } finally {
                this.loading = false;
            }
        },
        async createInstance(payload: ClaudeCodeInstanceInput) {
            this.creating = true;
            try {
                const item = await createClaudeCodeInstance({ ...payload, status: "active" });
                await this.loadInstances();
                return item;
            } finally {
                this.creating = false;
            }
        },
        async updateInstance(instanceId: number, payload: ClaudeCodeInstanceInput) {
            this.creating = true;
            try {
                const item = await updateClaudeCodeInstance(instanceId, payload);
                await this.loadInstances();
                return item;
            } finally {
                this.creating = false;
            }
        },
        async deleteInstance(instanceId: number) {
            this.savingId = `instance:${instanceId}:delete`;
            try {
                await deleteClaudeCodeInstance(instanceId);
                await this.loadInstances();
            } finally {
                this.savingId = null;
            }
        },
        async setInstanceEnabled(instanceId: number, enabled: boolean) {
            this.savingId = `instance:${instanceId}`;
            try {
                await (enabled ? enableClaudeCodeInstance(instanceId) : disableClaudeCodeInstance(instanceId));
                await this.loadInstances();
            } finally {
                this.savingId = null;
            }
        },
        async testInstance(instanceId: number) {
            this.savingId = `instance:${instanceId}:test`;
            try {
                const result = await testClaudeCodeInstance(instanceId);
                await this.loadInstances();
                return result;
            } finally {
                this.savingId = null;
            }
        },
        async openInstanceConversation(instanceId: number) {
            return await openClaudeCodeInstanceConversation(instanceId);
        },
    },
});
