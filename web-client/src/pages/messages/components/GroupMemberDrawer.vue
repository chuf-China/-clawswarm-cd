<template>
  <el-drawer
    :model-value="visible"
    :title="t('conversation.manageGroupMembers')"
    size="760px"
    destroy-on-close
    @close="emit('update:visible', false)"
  >
      <div v-if="group" class="member-drawer">
      <div class="member-dialog__intro">
          <div>
            <div class="member-dialog__group-name">{{ group.name }}</div>
            <div class="member-dialog__group-desc">{{ group.description || t("conversation.groupDescriptionEmpty") }}</div>
          </div>
          <el-button text type="danger" :disabled="saving" @click="emit('delete-group')">
            {{ t("common.delete") }}
          </el-button>
        </div>

      <div class="member-dialog__grid">
        <section class="member-card">
          <h3 class="member-card__title">{{ t("conversation.currentMembers") }}</h3>
          <div v-if="!group.members.length" class="member-card__empty">{{ t("conversation.noMembers") }}</div>
          <div v-for="member in group.members" :key="member.id" class="member-row">
            <div>
              <div class="member-row__title">{{ member.displayName }}</div>
              <div class="member-row__meta">
                <template v-if="member.runtimeType">
                  {{ member.instanceName || '' }} / {{ member.runtimeType }}
                </template>
                <template v-else>
                  {{ member.instanceName }} / {{ member.agentKey }}
                </template>
                <el-tag v-if="member.runtimeType === 'claude-code'" size="small" type="warning" effect="plain" style="margin-left: 6px">CC</el-tag>
                <el-tag v-else-if="member.runtimeType === 'hermes'" size="small" type="primary" effect="plain" style="margin-left: 6px">H</el-tag>
              </div>
            </div>
            <el-button text type="danger" :disabled="saving" @click="emit('remove-member', member.id)">
              {{ t("conversation.remove") }}
            </el-button>
          </div>
        </section>

        <section class="member-card">
          <h3 class="member-card__title">{{ t("conversation.addMembers") }}</h3>
          <div class="member-card__hint">{{ t("conversation.addMembersHint") }}</div>

          <el-select
            v-model="selectedValues"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            :placeholder="t('conversation.selectAgents')"
            style="width: 100%"
          >
            <el-option-group
              v-for="instance in instances"
              :key="`oc-${instance.id}`"
              :label="instance.name"
            >
              <el-option
                v-for="agent in instance.agents"
                :key="`oc:${instance.id}:${agent.id}`"
                :label="`${agent.displayName} / ${instance.name}`"
                :value="`oc:${instance.id}:${agent.id}`"
                :disabled="!agent.enabled || existingKeys.has(`oc:${instance.id}:${agent.id}`)"
              />
            </el-option-group>
            <el-option-group
              v-if="runtimeTargets.length"
              key="runtime-targets"
              :label="t('conversation.runtimeTargets')"
            >
              <el-option
                v-for="rt in runtimeTargets"
                :key="`rt:${rt.id}`"
                :label="`${rt.displayName} (${rt.runtimeType}) / ${rt.instanceName}`"
                :value="`rt:${rt.id}`"
                :disabled="!rt.enabled || existingKeys.has(`rt:${rt.id}`)"
              />
            </el-option-group>
          </el-select>

          <div class="member-card__actions">
            <el-button
              type="primary"
              :loading="saving"
              :disabled="!selectedValues.length"
              @click="submit"
            >
              {{ t("conversation.addMembers") }}
            </el-button>
          </div>
        </section>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
/**
 * 群成员管理抽屉。
 *
 * 支持查看成员、添加成员、移除成员和删除群组。
 */
import { computed, ref, watch } from "vue";

import { useI18n } from "@/composables/useI18n";
import type { AddressBookInstanceOutput, AddressBookRuntimeTargetOutput } from "@/types/view/addressBook";
import type { GroupDetailOutput, GroupMemberInput } from "@/types/view/group";

const props = defineProps<{
    visible: boolean;
    group: GroupDetailOutput | null;
    instances: AddressBookInstanceOutput[];
    runtimeTargets: AddressBookRuntimeTargetOutput[];
    saving: boolean;
}>();

const emit = defineEmits<{
    "update:visible": [value: boolean];
    "add-members": [payload: GroupMemberInput[]];
    "remove-member": [memberId: number];
    "delete-group": [];
}>();

const selectedValues = ref<string[]>([]);
const { t } = useI18n();

watch(
    () => props.visible,
    (visible) => {
        if (visible) {
            selectedValues.value = [];
        }
    },
);

const existingKeys = computed(() => {
    const values = new Set<string>();
    for (const member of props.group?.members ?? []) {
        if (member.runtimeTargetId) {
            values.add(`rt:${member.runtimeTargetId}`);
        } else if (member.instanceId && member.agentId) {
            values.add(`oc:${member.instanceId}:${member.agentId}`);
        }
    }
    return values;
});

function submit() {
    const payload = selectedValues.value.map((value): GroupMemberInput => {
        if (value.startsWith("oc:")) {
            const [, instanceId, agentId] = value.split(":").map(Number);
            return { instanceId, agentId };
        }
        if (value.startsWith("rt:")) {
            const runtimeTargetId = Number(value.split(":")[1]);
            return { runtimeTargetId };
        }
        return {};
    });
    emit("add-members", payload);
}
</script>

<style scoped>
.member-drawer {
  display: grid;
  gap: var(--space-4);
  padding-right: 6px;
}

.member-dialog__intro {
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.member-dialog__group-name {
  font-size: 1.05rem;
  font-weight: 700;
}

.member-dialog__group-desc {
  margin-top: 6px;
  color: var(--color-text-secondary);
}

.member-dialog__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.member-card {
  display: grid;
  align-content: start;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-app);
}

.member-card__title {
  margin: 0;
  font-size: 1rem;
}

.member-card__hint,
.member-card__empty {
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.member-card__actions {
  display: flex;
  justify-content: flex-end;
}

.member-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.member-row__title {
  font-weight: 600;
}

.member-row__meta {
  margin-top: 4px;
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}

@media (max-width: 900px) {
  .member-dialog__grid {
    grid-template-columns: 1fr;
  }
}
</style>
