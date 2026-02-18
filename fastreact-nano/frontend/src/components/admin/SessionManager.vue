<template>
  <div class="session-manager">
    <!-- Header -->
    <div class="manager-header">
      <div class="header-left">
        <h2>Active Sessions</h2>
        <el-tag type="info" size="large">{{ sessions.length }} Total</el-tag>
        <el-tag type="success" size="large">{{ activeCount }} Active</el-tag>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="Search sessions..."
          prefix-icon="Search"
          style="width: 250px"
          clearable
        />
        <el-button :icon="Refresh" @click="refreshSessions" :loading="refreshing">
          Refresh
        </el-button>
      </div>
    </div>

    <!-- Sessions Table -->
    <el-card class="sessions-card" shadow="never">
      <el-table
        :data="filteredSessions"
        stripe
        v-loading="loading"
        @row-click="viewSessionDetails"
        class="sessions-table"
      >
        <el-table-column prop="session_id" label="Session ID" width="200">
          <template #default="{ row }">
            <div class="session-id">
              <el-icon><Document /></el-icon>
              <span>{{ formatSessionId(row.session_id) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="Status" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="Created" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column prop="last_active" label="Last Active" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.last_active) }}
          </template>
        </el-table-column>

        <el-table-column prop="event_count" label="Events" width="100" align="center">
          <template #default="{ row }">
            <el-badge :value="row.event_count" :max="999" />
          </template>
        </el-table-column>

        <el-table-column prop="duration" label="Duration" width="120">
          <template #default="{ row }">
            {{ formatDuration(row.created_at, row.last_active) }}
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              :icon="View"
              @click.stop="viewSessionDetails(row)"
            >
              View
            </el-button>
            <el-button
              size="small"
              :icon="Download"
              @click.stop="exportSession(row)"
            >
              Export
            </el-button>
            <el-popconfirm
              v-if="row.status !== 'terminated'"
              title="Terminate this session?"
              @confirm="terminateSession(row.session_id)"
            >
              <template #reference>
                <el-button
                  size="small"
                  type="danger"
                  :icon="Close"
                  @click.stop
                />
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="sessions.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- Session Details Drawer -->
    <el-drawer
      v-model="detailsDrawerVisible"
      :title="`Session ${selectedSession ? formatSessionId(selectedSession.session_id) : ''}`"
      size="70%"
      class="session-drawer"
    >
      <div v-if="selectedSession" class="session-details">
        <!-- Session Info -->
        <el-descriptions :column="2" border class="session-info">
          <el-descriptions-item label="Session ID">
            <el-text tag="code">{{ selectedSession.session_id }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="Status">
            <el-tag :type="getStatusType(selectedSession.status)">
              {{ selectedSession.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Created">
            {{ formatDateTime(selectedSession.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="Last Active">
            {{ formatDateTime(selectedSession.last_active) }}
          </el-descriptions-item>
          <el-descriptions-item label="Duration">
            {{ formatDuration(selectedSession.created_at, selectedSession.last_active) }}
          </el-descriptions-item>
          <el-descriptions-item label="Total Events">
            {{ selectedSession.event_count }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- Session Actions -->
        <div class="drawer-actions">
          <el-button :icon="Refresh" @click="refreshSessionEvents">
            Refresh Events
          </el-button>
          <el-button :icon="Download" @click="exportSession(selectedSession)">
            Export Session
          </el-button>
          <el-button
            v-if="selectedSession.status !== 'terminated'"
            type="danger"
            :icon="Close"
            @click="terminateSession(selectedSession.session_id)"
          >
            Terminate Session
          </el-button>
        </div>

        <!-- Events Timeline -->
        <div class="events-section">
          <div class="events-header">
            <h3>Event Timeline</h3>
            <div class="events-filter">
              <el-select
                v-model="eventFilter"
                placeholder="Filter by type"
                clearable
                size="small"
                style="width: 150px"
              >
                <el-option label="All Events" value="" />
                <el-option label="Messages" value="message" />
                <el-option label="Tool Calls" value="tool_call" />
                <el-option label="Thinking" value="think" />
                <el-option label="Errors" value="error" />
              </el-select>
              <el-checkbox v-model="showTimestamps" size="small">
                Show Timestamps
              </el-checkbox>
            </div>
          </div>

          <div v-loading="loadingEvents" class="events-timeline">
            <el-empty v-if="filteredEvents.length === 0" description="No events found" />

            <el-timeline v-else>
              <el-timeline-item
                v-for="(event, index) in filteredEvents"
                :key="index"
                :timestamp="showTimestamps ? formatTimestamp(event.timestamp) : ''"
                :type="getEventType(event)"
                placement="top"
              >
                <div class="timeline-event" @click="expandEvent(index)">
                  <div class="event-header">
                    <el-tag :type="getEventType(event)" size="small">
                      {{ event.type?.replace('_', ' ').toUpperCase() }}
                    </el-tag>
                    <span class="event-summary">{{ getEventSummary(event) }}</span>
                  </div>

                  <el-collapse-transition>
                    <div v-show="expandedEvents.has(index)" class="event-details">
                      <!-- Message Event -->
                      <div v-if="event.type === 'message'" class="event-content">
                        <div class="message-role">
                          <el-icon>
                            <User v-if="event.role === 'user'" />
                            <Avatar v-else />
                          </el-icon>
                          <span>{{ event.role }}</span>
                        </div>
                        <div class="message-text">{{ event.content }}</div>
                      </div>

                      <!-- Tool Call Event -->
                      <div v-else-if="event.type === 'tool_call'" class="event-content">
                        <div class="tool-name">
                          <el-icon><Tools /></el-icon>
                          <span>{{ event.tool_name }}</span>
                        </div>
                        <el-collapse>
                          <el-collapse-item title="Parameters">
                            <pre class="event-json">{{ JSON.stringify(event.parameters, null, 2) }}</pre>
                          </el-collapse-item>
                        </el-collapse>
                      </div>

                      <!-- Tool Result Event -->
                      <div v-else-if="event.type === 'tool_result'" class="event-content">
                        <div class="result-status" :class="{ error: event.error }">
                          <el-icon>
                            <CircleCheck v-if="!event.error" />
                            <CircleClose v-else />
                          </el-icon>
                          <span>{{ event.error ? 'Error' : 'Success' }}</span>
                        </div>
                        <div v-if="event.result" class="result-content">
                          <pre class="event-json">{{ event.result }}</pre>
                        </div>
                        <div v-if="event.error" class="error-text">
                          {{ event.error }}
                        </div>
                      </div>

                      <!-- Thinking Event -->
                      <div v-else-if="event.type === 'think'" class="event-content">
                        <div class="thinking-content">
                          <pre>{{ event.content }}</pre>
                        </div>
                      </div>

                      <!-- Error Event -->
                      <div v-else-if="event.type === 'error'" class="event-content">
                        <el-alert
                          :title="event.error"
                          :description="event.details"
                          type="error"
                          :closable="false"
                        />
                      </div>

                      <!-- Default Event -->
                      <div v-else class="event-content">
                        <pre class="event-json">{{ JSON.stringify(event, null, 2) }}</pre>
                      </div>
                    </div>
                  </el-collapse-transition>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- Export Dialog -->
    <el-dialog
      v-model="exportDialogVisible"
      title="Export Session"
      width="500px"
    >
      <el-form label-width="100px">
        <el-form-item label="Format">
          <el-radio-group v-model="exportFormat">
            <el-radio label="json">JSON</el-radio>
            <el-radio label="txt">Plain Text</el-radio>
            <el-radio label="md">Markdown</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="Include">
          <el-checkbox-group v-model="exportOptions">
            <el-checkbox label="events">Events</el-checkbox>
            <el-checkbox label="metadata">Metadata</el-checkbox>
            <el-checkbox label="config">Configuration</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="doExport" :loading="exporting">
          Export
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Document,
  View,
  Download,
  Close,
  Refresh,
  Search,
  User,
  Avatar,
  Tools,
  CircleCheck,
  CircleClose,
} from "@element-plus/icons-vue";
import { useAPI } from "../../services/api";
import { useSessionStore } from "../../stores/session";
import { useEventsStore } from "../../stores/events";

const api = useAPI();
const sessionStore = useSessionStore();
const eventsStore = useEventsStore();

// State
const sessions = ref<any[]>([]);
const loading = ref(false);
const refreshing = ref(false);
const searchQuery = ref("");
const currentPage = ref(1);
const pageSize = ref(20);

const selectedSession = ref<any>(null);
const detailsDrawerVisible = ref(false);
const sessionEvents = ref<any[]>([]);
const loadingEvents = ref(false);

const eventFilter = ref("");
const showTimestamps = ref(true);
const expandedEvents = ref(new Set<number>());

const exportDialogVisible = ref(false);
const exportFormat = ref("json");
const exportOptions = ref(["events", "metadata"]);
const exporting = ref(false);

// Computed
const filteredSessions = computed(() => {
  let filtered = sessions.value;

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter((s) =>
      s.session_id.toLowerCase().includes(query)
    );
  }

  const start = (currentPage.value - 1) * pageSize.value;
  return filtered.slice(start, start + pageSize.value);
});

const activeCount = computed(() => {
  return sessions.value.filter((s) => s.status === "active").length;
});

const filteredEvents = computed(() => {
  let events = sessionEvents.value;

  if (eventFilter.value) {
    events = events.filter((e) => e.type === eventFilter.value);
  }

  return events;
});

// Methods
function formatSessionId(id: string): string {
  return id.substring(0, 12);
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleString();
}

function formatTimestamp(dateStr: string): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleTimeString();
}

function formatDuration(start: string, end: string): string {
  if (!start || !end) return "-";
  const startDate = new Date(start);
  const endDate = new Date(end);
  const diff = Math.floor((endDate.getTime() - startDate.getTime()) / 1000);

  const hours = Math.floor(diff / 3600);
  const minutes = Math.floor((diff % 3600) / 60);
  const seconds = diff % 60;

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function getStatusType(status: string): "success" | "info" | "warning" | "danger" {
  const statusMap: Record<string, "success" | "info" | "warning" | "danger"> = {
    active: "success",
    idle: "info",
    terminated: "danger",
    error: "danger",
  };
  return statusMap[status] || "info";
}

function getEventType(event: any): "success" | "warning" | "danger" | "info" | "primary" {
  const typeMap: Record<string, "success" | "warning" | "danger" | "info" | "primary"> = {
    message: "primary",
    tool_call: "warning",
    tool_result: "success",
    think: "info",
    error: "danger",
  };
  return typeMap[event.type] || "info";
}

function getEventSummary(event: any): string {
  switch (event.type) {
    case "message":
      return `${event.role}: ${event.content?.substring(0, 50) || "Empty"}...`;
    case "tool_call":
      return `Called ${event.tool_name}`;
    case "tool_result":
      return event.error ? "Failed" : "Completed";
    case "think":
      return event.content?.substring(0, 50) || "Thinking...";
    default:
      return event.type || "Unknown";
  }
}

function expandEvent(index: number) {
  if (expandedEvents.value.has(index)) {
    expandedEvents.value.delete(index);
  } else {
    expandedEvents.value.add(index);
  }
}

async function refreshSessions() {
  refreshing.value = true;

  try {
    const data = await api.listSessions();
    sessions.value = data.sessions || [];
    ElMessage.success(`Loaded ${sessions.value.length} sessions`);
  } catch (error: any) {
    ElMessage.error(`Failed to load sessions: ${error.message}`);
  } finally {
    refreshing.value = false;
  }
}

async function viewSessionDetails(session: any) {
  selectedSession.value = session;
  detailsDrawerVisible.value = true;
  await refreshSessionEvents();
}

async function refreshSessionEvents() {
  if (!selectedSession.value) return;

  loadingEvents.value = true;

  try {
    // Get events from store or API
    const events = eventsStore.getEventsForSession(selectedSession.value.session_id);

    if (events.length > 0) {
      sessionEvents.value = events;
    } else {
      // Fetch from API
      const history = await api.getSessionHistory(selectedSession.value.session_id);
      sessionEvents.value = history.events || [];
    }

    ElMessage.success(`Loaded ${sessionEvents.value.length} events`);
  } catch (error: any) {
    ElMessage.error(`Failed to load events: ${error.message}`);
  } finally {
    loadingEvents.value = false;
  }
}

async function terminateSession(sessionId: string) {
  try {
    await api.terminateSession(sessionId);

    // Update local state
    const session = sessions.value.find((s) => s.session_id === sessionId);
    if (session) {
      session.status = "terminated";
    }

    sessionStore.removeSession(sessionId);
    eventsStore.removeSession(sessionId);

    ElMessage.success("Session terminated");
    await refreshSessions();
  } catch (error: any) {
    ElMessage.error(`Failed to terminate: ${error.message}`);
  }
}

function exportSession(session: any) {
  selectedSession.value = session;
  exportDialogVisible.value = true;
}

async function doExport() {
  exporting.value = true;

  try {
    const data = {
      session: selectedSession.value,
      events: exportOptions.value.includes("events") ? sessionEvents.value : [],
      metadata: exportOptions.value.includes("metadata") ? {
        exported_at: new Date().toISOString(),
        export_format: exportFormat.value,
      } : {},
    };

    let content: string;
    let filename: string;
    let mimeType: string;

    if (exportFormat.value === "json") {
      content = JSON.stringify(data, null, 2);
      filename = `session-${formatSessionId(selectedSession.value.session_id)}.json`;
      mimeType = "application/json";
    } else if (exportFormat.value === "md") {
      content = generateMarkdown(data);
      filename = `session-${formatSessionId(selectedSession.value.session_id)}.md`;
      mimeType = "text/markdown";
    } else {
      content = generatePlainText(data);
      filename = `session-${formatSessionId(selectedSession.value.session_id)}.txt`;
      mimeType = "text/plain";
    }

    // Download file
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);

    ElMessage.success("Session exported");
    exportDialogVisible.value = false;
  } catch (error: any) {
    ElMessage.error(`Export failed: ${error.message}`);
  } finally {
    exporting.value = false;
  }
}

function generateMarkdown(data: any): string {
  let md = `# Session ${formatSessionId(data.session.session_id)}\n\n`;
  md += `**Status:** ${data.session.status}\n`;
  md += `**Created:** ${formatDateTime(data.session.created_at)}\n`;
  md += `**Duration:** ${formatDuration(data.session.created_at, data.session.last_active)}\n\n`;
  md += `## Events\n\n`;

  for (const event of data.events) {
    md += `### ${event.type?.toUpperCase()}\n`;
    md += `**Time:** ${formatDateTime(event.timestamp)}\n\n`;

    if (event.type === "message") {
      md += `**Role:** ${event.role}\n\n`;
      md += `${event.content}\n\n`;
    } else if (event.type === "tool_call") {
      md += `**Tool:** ${event.tool_name}\n\n`;
      md += `**Parameters:**\n\`\`\`json\n${JSON.stringify(event.parameters, null, 2)}\n\`\`\`\n\n`;
    } else if (event.type === "tool_result") {
      md += `**Result:**\n\`\`\`\n${event.result}\n\`\`\`\n\n`;
    }
  }

  return md;
}

function generatePlainText(data: any): string {
  let text = `Session: ${data.session.session_id}\n`;
  text += `Status: ${data.session.status}\n`;
  text += `Created: ${formatDateTime(data.session.created_at)}\n\n`;
  text += `Events:\n`;
  text += `${"=".repeat(80)}\n\n`;

  for (const event of data.events) {
    text += `[${formatDateTime(event.timestamp)}] ${event.type?.toUpperCase()}\n`;

    if (event.type === "message") {
      text += `  Role: ${event.role}\n`;
      text += `  Content: ${event.content}\n\n`;
    } else if (event.type === "tool_call") {
      text += `  Tool: ${event.tool_name}\n`;
      text += `  Parameters: ${JSON.stringify(event.parameters)}\n\n`;
    }

    text += `${"-".repeat(80)}\n\n`;
  }

  return text;
}

function handleSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
}

function handleCurrentChange(page: number) {
  currentPage.value = page;
}

// Lifecycle
onMounted(() => {
  refreshSessions();
});
</script>

<style scoped>
.session-manager {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Header */
.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-left h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 0.75rem;
}

/* Sessions Card */
.sessions-card {
  width: 100%;
}

.sessions-table {
  width: 100%;
}

.session-id {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: monospace;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: 1rem 0;
  margin-top: 1rem;
}

/* Drawer */
.session-drawer :deep(.el-drawer__body) {
  padding: 0;
}

.session-details {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.session-info {
  margin-bottom: 0;
}

.drawer-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

/* Events Section */
.events-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.events-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--el-border-color);
}

.events-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.events-filter {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.events-timeline {
  max-height: 60vh;
  overflow-y: auto;
}

.timeline-event {
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  transition: background 0.2s;
}

.timeline-event:hover {
  background: var(--el-fill-color-light);
}

.event-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.event-summary {
  flex: 1;
  font-size: 0.875rem;
}

.event-details {
  margin-top: 0.75rem;
  padding: 1rem;
  background: var(--el-fill-color-blank);
  border-radius: 4px;
}

.event-content {
  font-size: 0.875rem;
}

.message-role {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.message-text {
  padding: 0.75rem;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  white-space: pre-wrap;
}

.tool-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--el-color-warning);
  margin-bottom: 0.5rem;
}

.result-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.result-status.error {
  color: var(--el-color-danger);
}

.result-status:not(.error) {
  color: var(--el-color-success);
}

.result-content {
  padding: 0.75rem;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.error-text {
  padding: 0.75rem;
  background: var(--el-color-danger-light-9);
  border-radius: 4px;
  color: var(--el-color-danger);
}

.thinking-content {
  padding: 0.75rem;
  background: var(--el-color-info-light-9);
  border-radius: 4px;
  font-style: italic;
}

.event-json {
  margin: 0;
  padding: 0.75rem;
  background: var(--el-bg-color-page);
  border-radius: 4px;
  font-size: 0.75rem;
  overflow-x: auto;
  white-space: pre-wrap;
}

/* Responsive */
@media (max-width: 768px) {
  .manager-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-left,
  .header-right {
    flex-direction: column;
    width: 100%;
  }

  .header-right .el-input {
    width: 100% !important;
  }
}
</style>
