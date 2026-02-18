<template>
  <div class="chat-view">
    <!-- Sidebar -->
    <aside class="chat-sidebar">
      <div class="sidebar-header">
        <h2>FastReAct</h2>
        <el-button type="primary" @click="createNewSession" circle>
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>

      <div class="sidebar-content">
        <div class="session-list">
          <div
            v-for="session in sessionStore.sessions"
            :key="session.session_id"
            class="session-item"
            :class="{ active: session.session_id === sessionStore.currentSessionId }"
            @click="selectSession(session.session_id)"
          >
            <div class="session-info">
              <span class="session-title">Session {{ formatSessionId(session.session_id) }}</span>
              <span class="session-time">{{ formatTime(session.last_active) }}</span>
            </div>
            <el-button
              size="small"
              type="danger"
              :icon="Delete"
              circle
              @click.stop="deleteSession(session.session_id)"
            />
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="chat-main">
      <!-- Header -->
      <header class="chat-header">
        <div class="header-left">
          <h1>Chat</h1>
          <el-tag v-if="wsStatus === 'connected'" type="success">Connected</el-tag>
          <el-tag v-else-if="wsStatus === 'connecting'" type="warning">Connecting...</el-tag>
          <el-tag v-else type="danger">Disconnected</el-tag>
        </div>

        <div class="header-right">
          <el-button @click="toggleTheme" :icon="isDark ? Sunny : Moon" circle />
        </div>
      </header>

      <!-- Messages -->
      <div class="chat-messages" ref="messagesContainer">
        <div v-if="events.length === 0" class="empty-state">
          <el-icon class="empty-icon"><ChatDotSquare /></el-icon>
          <h3>No messages yet</h3>
          <p>Start a conversation by typing a message below.</p>
        </div>

        <div v-else class="messages-list">
          <EventRenderer
            v-for="(event, index) in events"
            :key="index"
            :event="event"
          />
        </div>

        <!-- Thinking Indicator -->
        <div v-if="isStreaming" class="thinking-indicator">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>Thinking...</span>
        </div>
      </div>

      <!-- Input -->
      <div class="chat-input">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="inputRows"
          placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
          @keydown.enter.exact="sendMessage"
          @keydown.enter.shift.prevent="inputRows += 1"
          :disabled="wsStatus !== 'connected' || isStreaming"
        />
        <div class="input-actions">
          <span class="input-hint">{{ inputHint }}</span>
          <el-button
            type="primary"
            @click="sendMessage"
            :disabled="!inputMessage.trim() || wsStatus !== 'connected' || isStreaming"
            :loading="isStreaming"
          >
            Send
          </el-button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Delete, Moon, Sunny, ChatDotSquare, Loading } from "@element-plus/icons-vue";
import { useWebSocket } from "../services/websocket";
import { useEventStream } from "../composables/useEventStream";
import { useTheme } from "../composables/useTheme";
import { useSessionStore } from "../stores/session";
import { useEventsStore } from "../stores/events";
import EventRenderer from "../components/common/EventRenderer.vue";

// Services and stores
const { client: wsClient, status: wsStatus, connect: wsConnect } = useWebSocket();
const { sendQuery, subscribe: subscribeToEvents } = useEventStream(wsClient);
const { isDark, toggleTheme } = useTheme();
const sessionStore = useSessionStore();
const eventsStore = useEventsStore();

// State
const inputMessage = ref("");
const inputRows = ref(1);
const messagesContainer = ref<HTMLElement | null>(null);

// Computed
const events = computed(() => eventsStore.currentSessionEvents);
const isStreaming = computed(() => eventsStore.isStreaming);

const inputHint = computed(() => {
  if (wsStatus.value !== "connected") {
    return "⚠️ Not connected to server";
  }
  if (isStreaming.value) {
    return "⏳ Agent is working...";
  }
  return "⌨️ Enter to send, Shift+Enter for new line";
});

// Methods
async function sendMessage() {
  const message = inputMessage.value.trim();
  if (!message) return;

  if (wsStatus.value !== "connected") {
    ElMessage.error("Not connected to server");
    return;
  }

  if (isStreaming.value) {
    ElMessage.warning("Please wait for the current response to complete");
    return;
  }

  try {
    sendQuery(message);
    inputMessage.value = "";
    inputRows.value = 1;

    // Add user message to events
    eventsStore.addEvent({
      type: "message",
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    });

    await scrollToBottom();
  } catch (error: any) {
    ElMessage.error(`Failed to send message: ${error.message}`);
  }
}

function createNewSession() {
  eventsStore.clearCurrentSession();
  sessionStore.setCurrentSession(null);
  ElMessage.success("Started new session");
}

function selectSession(sessionId: string) {
  sessionStore.setCurrentSession(sessionId);
  const sessionEvents = eventsStore.getEventsForSession(sessionId);
  // Load session events
  ElMessage.info("Session loaded");
}

async function deleteSession(sessionId: string) {
  try {
    await ElMessageBox.confirm(
      "Are you sure you want to delete this session?",
      "Delete Session",
      {
        confirmButtonText: "Delete",
        cancelButtonText: "Cancel",
        type: "warning",
      }
    );

    sessionStore.removeSession(sessionId);
    eventsStore.removeSession(sessionId);
    ElMessage.success("Session deleted");
  } catch {
    // User cancelled
  }
}

function formatSessionId(sessionId: string): string {
  return sessionId.substring(0, 8);
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  if (diff < 60000) return "Just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
}

async function scrollToBottom() {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

// Lifecycle
onMounted(() => {
  wsConnect();
  subscribeToEvents();
});

watch(events, () => {
  scrollToBottom();
}, { deep: true });
</script>

<style scoped>
.chat-view {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* Sidebar */
.chat-sidebar {
  width: 280px;
  background-color: var(--el-bg-color-page);
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 1rem;
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.session-item:hover {
  background-color: var(--el-fill-color-light);
}

.session-item.active {
  background-color: var(--el-color-primary-light-9);
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.session-title {
  font-weight: 500;
}

.session-time {
  font-size: 0.75rem;
  color: var(--el-text-color-secondary);
}

/* Main Chat Area */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  padding: 1rem;
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-left h1 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
}

.empty-state p {
  margin: 0;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  color: var(--el-text-color-secondary);
}

.chat-input {
  padding: 1rem;
  border-top: 1px solid var(--el-border-color);
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
}

.input-hint {
  font-size: 0.75rem;
  color: var(--el-text-color-secondary);
}
</style>
