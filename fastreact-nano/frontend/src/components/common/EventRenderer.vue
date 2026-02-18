<template>
  <div class="event-renderer" :class="`event-${event.type}`">
    <!-- THINK Event -->
    <div v-if="event.type === 'think'" class="think-event">
      <el-collapse>
        <el-collapse-item>
          <template #title>
            <el-icon class="think-icon"><ThinkIcon /></el-icon>
            <span class="think-label">Thinking</span>
          </template>
          <div class="think-content">
            <pre>{{ event.content }}</pre>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- TOOL_CALL Event -->
    <div v-else-if="event.type === 'tool_call'" class="tool-call-event">
      <div class="tool-header">
        <el-icon class="tool-icon"><ToolsIcon /></el-icon>
        <span class="tool-name">{{ event.tool_name }}</span>
        <el-tag size="small" type="info">CALL</el-tag>
      </div>
      <div class="tool-params">
        <h4>Parameters:</h4>
        <pre class="params-code">{{ formatJSON(event.parameters) }}</pre>
      </div>
    </div>

    <!-- TOOL_RESULT Event -->
    <div v-else-if="event.type === 'tool_result'" class="tool-result-event">
      <div class="result-header">
        <el-icon class="result-icon" :class="{ 'result-error': event.error }">
          <CheckIcon v-if="!event.error" />
          <CloseIcon v-else />
        </el-icon>
        <span class="result-label">Result</span>
        <el-tag
          size="small"
          :type="event.error ? 'danger' : 'success'"
        >
          {{ event.error ? "ERROR" : "SUCCESS" }}
        </el-tag>
      </div>
      <div class="result-content">
        <pre class="result-code" v-if="event.result">{{ event.result }}</pre>
        <div v-if="event.error" class="error-message">{{ event.error }}</div>
      </div>
    </div>

    <!-- ERROR Event -->
    <div v-else-if="event.type === 'error'" class="error-event">
      <el-alert
        :title="event.error"
        :description="event.details"
        type="error"
        :closable="false"
        show-icon
      />
    </div>

    <!-- MESSAGE Event -->
    <div v-else-if="event.type === 'message'" class="message-event">
      <div class="message-header">
        <el-icon class="role-icon" :class="`role-${event.role}`">
          <UserIcon v-if="event.role === 'user'" />
          <RobotIcon v-else-if="event.role === 'assistant'" />
          <SettingIcon v-else />
        </el-icon>
        <span class="role-label">{{ formatRole(event.role) }}</span>
        <span class="message-time">{{ formatTime(event.timestamp) }}</span>
      </div>
      <div class="message-content">
        <MarkdownView :content="event.content || ''" />
      </div>
    </div>

    <!-- SESSION_START Event -->
    <div v-else-if="event.type === 'session_start'" class="session-start-event">
      <el-tag type="success">Session Started</el-tag>
      <span class="session-id">{{ event.session_id }}</span>
    </div>

    <!-- SESSION_END Event -->
    <div v-else-if="event.type === 'session_end'" class="session-end-event">
      <el-tag type="info">Session Ended</el-tag>
      <span class="session-summary" v-if="event.summary">{{ event.summary }}</span>
    </div>

    <!-- Unknown Event -->
    <div v-else class="unknown-event">
      <el-alert
        title="Unknown Event"
        :description="JSON.stringify(event, null, 2)"
        type="warning"
        :closable="false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import MarkdownIt from "markdown-it";
import type { AgentEvent } from "../../types/events";
import MarkdownView from "./MarkdownView.vue";

// Icons (placeholder - will be replaced with Element Plus icons)
const ThinkIcon = "💭";
const ToolsIcon = "🔧";
const CheckIcon = "✓";
const CloseIcon = "✗";
const UserIcon = "👤";
const RobotIcon = "🤖";
const SettingIcon = "⚙️";

const props = defineProps<{
  event: AgentEvent;
}>();

function formatJSON(obj: any): string {
  return JSON.stringify(obj, null, 2);
}

function formatTime(timestamp: string | undefined): string {
  if (!timestamp) return "";

  const date = new Date(timestamp);
  return date.toLocaleTimeString();
}

function formatRole(role: string): string {
  const roleMap: Record<string, string> = {
    user: "You",
    assistant: "Assistant",
    system: "System",
  };

  return roleMap[role] || role;
}
</script>

<style scoped>
.event-renderer {
  margin-bottom: 1rem;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background-color: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color);
}

/* Think Event */
.think-event {
  border-left: 3px solid #409eff;
}

.think-icon {
  margin-right: 0.5rem;
  color: #409eff;
}

.think-label {
  font-style: italic;
  color: #409eff;
}

.think-content pre {
  margin: 0;
  padding: 0.75rem;
  background-color: var(--el-bg-color);
  border-radius: 0.25rem;
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Tool Call Event */
.tool-call-event {
  border-left: 3px solid #e6a23c;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.tool-icon {
  color: #e6a23c;
}

.tool-name {
  font-weight: 600;
}

.tool-params h4 {
  margin: 0.5rem 0;
  font-size: 0.875rem;
  color: var(--el-text-color-secondary);
}

.params-code {
  margin: 0;
  padding: 0.75rem;
  background-color: var(--el-bg-color);
  border-radius: 0.25rem;
  font-size: 0.875rem;
  overflow-x: auto;
}

/* Tool Result Event */
.tool-result-event {
  border-left: 3px solid #67c23a;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.result-icon {
  color: #67c23a;
}

.result-icon.result-error {
  color: #f56c6c;
}

.result-code {
  margin: 0;
  padding: 0.75rem;
  background-color: var(--el-bg-color);
  border-radius: 0.25rem;
  font-size: 0.875rem;
  overflow-x: auto;
}

.error-message {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background-color: #fef0f0;
  border-radius: 0.25rem;
  color: #f56c6c;
}

/* Error Event */
.error-event {
  border-left: 3px solid #f56c6c;
}

/* Message Event */
.message-event {
  border-left: 3px solid var(--el-border-color);
}

.message-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.role-icon {
  font-size: 1.25rem;
}

.role-label {
  font-weight: 600;
}

.message-time {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--el-text-color-secondary);
}

.message-content {
  padding: 0.5rem 0;
}

/* Session Events */
.session-start-event,
.session-end-event {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  text-align: center;
}

.session-id,
.session-summary {
  font-family: monospace;
  font-size: 0.875rem;
  color: var(--el-text-color-secondary);
}

/* Dark mode support */
.dark .think-content pre,
.dark .params-code,
.dark .result-code {
  background-color: #1d1e1f;
  color: #e0e0e0;
}
</style>
