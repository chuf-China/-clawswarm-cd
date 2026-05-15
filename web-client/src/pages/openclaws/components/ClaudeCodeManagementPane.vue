<template>
  <section class="cc-pane" v-loading="pageBusy">
    <el-card shadow="never">
      <template #header>
        <div class="cc-pane__header">
          <el-space wrap>
            <h2 class="page-section-title">{{ t("claudeCode.instanceList") }}</h2>
            <el-tag type="info" effect="plain">{{ instances.length }}</el-tag>
          </el-space>
          <el-button type="primary" @click="openCreate">
            {{ t("claudeCode.addInstance") }}
          </el-button>
        </div>
      </template>

      <el-empty v-if="store.loading && !instances.length" :description="t('claudeCode.loadingInstances')" />
      <el-empty v-else-if="!instances.length" :description="t('claudeCode.noInstances')" />

      <div v-else class="cc-pane__list">
        <el-card v-for="inst in instances" :key="inst.id" shadow="hover" class="cc-instance-card">
          <div class="cc-instance-card__header">
            <div class="cc-instance-card__main">
              <el-space wrap>
                <strong>{{ inst.displayName }}</strong>
                <el-tag type="info" effect="plain">{{ inst.csId }}</el-tag>
                <el-tag :type="inst.status === 'active' ? 'success' : 'info'" effect="plain">
                  {{ inst.status === "active" ? t("openclaw.online") : t("openclaw.inactive") }}
                </el-tag>
                <el-tag v-if="inst.toolsConfigured" type="warning" effect="plain">tools</el-tag>
              </el-space>
              <p class="cc-instance-card__meta">
                {{ inst.name }} · {{ inst.roleName || t("claudeCode.noRole") }}
              </p>
              <p class="cc-instance-card__url">{{ inst.workspaceDir }}</p>
            </div>
            <el-space wrap>
              <el-tooltip :content="t('claudeCode.chat')" placement="top">
                <el-button circle type="primary" @click="openConversation(inst)">
                  <el-icon><ChatDotRound /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip :content="t('claudeCode.testConnection')" placement="top">
                <el-button circle @click="testInstance(inst)">
                  <el-icon><Connection /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip :content="t('common.edit')" placement="top">
                <el-button circle @click="openEdit(inst)">
                  <el-icon><EditPen /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip :content="inst.status === 'active' ? t('common.disable') : t('common.enable')" placement="top">
                <el-button circle :type="inst.status === 'active' ? 'warning' : 'success'" @click="toggleInstance(inst)">
                  <el-icon>
                    <component :is="inst.status === 'active' ? SwitchButton : VideoPlay" />
                  </el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip :content="t('common.delete')" placement="top">
                <el-button circle type="danger" @click="confirmDelete(inst)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </el-space>
          </div>
        </el-card>
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="drawerTitle" size="560px">
      <el-form label-position="top">
        <el-form-item :label="t('claudeCode.instanceName')">
          <el-input v-model="form.name" maxlength="120" />
        </el-form-item>
        <el-form-item :label="t('claudeCode.displayName')">
          <el-input v-model="form.displayName" maxlength="120" />
        </el-form-item>
        <el-form-item :label="t('claudeCode.roleName')">
          <el-input v-model="form.roleName" maxlength="120" placeholder="e.g. developer, designer" />
        </el-form-item>
        <el-form-item :label="t('claudeCode.workspaceDir')">
          <el-input v-model="form.workspaceDir" maxlength="500" placeholder="/tmp/cc-agent-1" />
        </el-form-item>
        <el-form-item :label="t('claudeCode.allowedTools')">
          <el-select v-model="form.allowedTools" multiple placeholder="Select tools" style="width: 100%">
            <el-option label="Read" value="Read" />
            <el-option label="Edit" value="Edit" />
            <el-option label="Bash" value="Bash" />
            <el-option label="WebSearch" value="WebSearch" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('claudeCode.modelOverride')">
          <el-input v-model="form.modelOverride" maxlength="120" placeholder="deepseek-v4-flash" />
        </el-form-item>
        <el-form-item :label="t('claudeCode.systemPrompt')">
          <el-input
            v-model="form.systemPrompt"
            type="textarea"
            :rows="4"
            placeholder="Optional: system prompt for this agent's role"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="drawerVisible = false">{{ t("common.cancel") }}</el-button>
        <el-button type="primary" @click="submitForm">{{ t("common.save") }}</el-button>
      </template>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ChatDotRound, Connection, Delete, EditPen, SwitchButton, VideoPlay } from "@element-plus/icons-vue";

import { useI18n } from "@/composables/useI18n";
import { useClaudeCodeStore } from "@/stores/claude-code";
import { useConversationStore } from "@/stores/conversation";
import type { ClaudeCodeInstanceOutput } from "@/types/view/claude-code";

const store = useClaudeCodeStore();
const conversationStore = useConversationStore();
const router = useRouter();
const { t } = useI18n();

const drawerVisible = ref(false);
const mode = ref<"create" | "edit">("create");
const editingId = ref<number | null>(null);

const form = reactive({
    name: "",
    displayName: "",
    roleName: "",
    workspaceDir: "",
    allowedTools: [] as string[],
    modelOverride: "",
    systemPrompt: "",
});

const instances = computed(() => store.instances);
const pageBusy = computed(() => store.loading || store.creating || store.savingId !== null);
const drawerTitle = computed(() =>
    mode.value === "create" ? t("claudeCode.addInstance") : t("claudeCode.editInstance")
);

onMounted(async () => {
    if (!instances.value.length) {
        await store.loadInstances();
    }
});

function resetForm() {
    form.name = "";
    form.displayName = "";
    form.roleName = "";
    form.workspaceDir = "";
    form.allowedTools = [];
    form.modelOverride = "";
    form.systemPrompt = "";
}

function openCreate() {
    mode.value = "create";
    editingId.value = null;
    resetForm();
    drawerVisible.value = true;
}

function openEdit(inst: ClaudeCodeInstanceOutput) {
    mode.value = "edit";
    editingId.value = inst.id;
    form.name = inst.name;
    form.displayName = inst.displayName;
    form.roleName = inst.roleName ?? "";
    form.workspaceDir = inst.workspaceDir;
    form.allowedTools = inst.allowedTools ?? [];
    form.modelOverride = inst.modelOverride ?? "";
    form.systemPrompt = inst.systemPrompt ?? "";
    drawerVisible.value = true;
}

async function submitForm() {
    const payload = {
        name: form.name,
        displayName: form.displayName,
        roleName: form.roleName || null,
        workspaceDir: form.workspaceDir,
        allowedTools: form.allowedTools.length > 0 ? form.allowedTools : null,
        modelOverride: form.modelOverride || null,
        systemPrompt: form.systemPrompt || null,
    };
    try {
        if (mode.value === "edit" && editingId.value !== null) {
            await store.updateInstance(editingId.value, payload);
        } else {
            await store.createInstance(payload);
        }
        drawerVisible.value = false;
    } catch (error) {
        ElMessage.error(error instanceof Error ? error.message : String(error));
    }
}

async function testInstance(inst: ClaudeCodeInstanceOutput) {
    try {
        await store.testInstance(inst.id);
        ElMessage.success(t("claudeCode.testSuccess"));
    } catch (error) {
        ElMessage.error(error instanceof Error ? error.message : String(error));
    }
}

async function toggleInstance(inst: ClaudeCodeInstanceOutput) {
    await store.setInstanceEnabled(inst.id, inst.status !== "active");
}

async function confirmDelete(inst: ClaudeCodeInstanceOutput) {
    try {
        await ElMessageBox.confirm(
            t("claudeCode.deleteConfirm", { name: inst.displayName }),
            t("common.confirm"),
            { type: "warning", confirmButtonText: t("common.confirm"), cancelButtonText: t("common.cancel") }
        );
    } catch {
        return;
    }
    await store.deleteInstance(inst.id);
}

async function openConversation(inst: ClaudeCodeInstanceOutput) {
    try {
        const conversation = await store.openInstanceConversation(inst.id);
        await conversationStore.openConversation(conversation.id, conversation);
        await router.push(`/messages/conversation/${conversation.id}`);
    } catch (error) {
        ElMessage.error(error instanceof Error ? error.message : String(error));
    }
}
</script>

<style scoped>
.cc-pane__header,
.cc-instance-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-3);
}

.cc-pane__list {
    display: grid;
    gap: var(--space-4);
}

.cc-instance-card__main {
    min-width: 0;
}

.cc-instance-card__meta,
.cc-instance-card__url {
    margin: var(--space-1) 0 0;
    color: var(--color-text-secondary);
    font-size: 13px;
}

.cc-instance-card__url {
    word-break: break-all;
}

@media (max-width: 960px) {
    .cc-pane__header,
    .cc-instance-card__header {
        flex-direction: column;
    }
}
</style>
