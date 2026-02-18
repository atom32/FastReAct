<template>
  <div class="dashboard">
    <!-- Metrics Cards -->
    <el-row :gutter="20" class="metrics-row">
      <el-col :xs="12" :sm="6" :md="6" :lg="6">
        <el-card class="metric-card" shadow="hover">
          <div class="metric-content">
            <div class="metric-icon active-sessions">
              <el-icon><User /></el-icon>
            </div>
            <div class="metric-info">
              <div class="metric-value">{{ metrics.activeSessions }}</div>
              <div class="metric-label">Active Sessions</div>
            </div>
          </div>
          <div class="metric-trend" :class="{ positive: sessionTrend > 0, negative: sessionTrend < 0 }">
            <el-icon><CaretTop v-if="sessionTrend > 0" /><CaretBottom v-else /></el-icon>
            <span>{{ Math.abs(sessionTrend) }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="6">
        <el-card class="metric-card" shadow="hover">
          <div class="metric-content">
            <div class="metric-icon total-events">
              <el-icon><DataLine /></el-icon>
            </div>
            <div class="metric-info">
              <div class="metric-value">{{ formatNumber(metrics.totalEvents) }}</div>
              <div class="metric-label">Total Events</div>
            </div>
          </div>
          <div class="metric-trend positive">
            <el-icon><CaretTop /></el-icon>
            <span>{{ formatNumber(eventRate) }}/min</span>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="6">
        <el-card class="metric-card" shadow="hover">
          <div class="metric-content">
            <div class="metric-icon uptime">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="metric-info">
              <div class="metric-value">{{ formatUptime(metrics.uptime) }}</div>
              <div class="metric-label">Uptime</div>
            </div>
          </div>
          <div class="metric-footer">
            <span>Since {{ startTime }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="6">
        <el-card class="metric-card" shadow="hover">
          <div class="metric-content">
            <div class="metric-icon memory">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="metric-info">
              <div class="metric-value">{{ metrics.memoryUsage }}MB</div>
              <div class="metric-label">Memory Usage</div>
            </div>
          </div>
          <el-progress
            :percentage="memoryPercent"
            :color="memoryColor"
            :show-text="false"
            class="metric-progress"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts Row -->
    <el-row :gutter="20" class="charts-row">
      <el-col :xs="24" :sm="24" :md="16" :lg="16">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>Events Over Time</span>
              <div class="header-actions">
                <el-radio-group v-model="chartTimeRange" size="small">
                  <el-radio-button label="1h">1H</el-radio-button>
                  <el-radio-button label="6h">6H</el-radio-button>
                  <el-radio-button label="24h">24H</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <div class="chart-container" ref="eventsChartRef">
            <div class="chart-placeholder">
              <el-icon class="chart-icon"><TrendCharts /></el-icon>
              <p>Events chart will be rendered here</p>
              <p class="placeholder-text">Install ECharts or Chart.js for visualization</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="24" :md="8" :lg="8">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>System Health</span>
            </div>
          </template>
          <div class="health-status">
            <div class="health-item">
              <div class="health-label">WebSocket</div>
              <el-tag :type="wsConnected ? 'success' : 'danger'" size="large">
                {{ wsConnected ? 'Connected' : 'Disconnected' }}
              </el-tag>
            </div>
            <div class="health-item">
              <div class="health-label">API Server</div>
              <el-tag type="success" size="large">Operational</el-tag>
            </div>
            <div class="health-item">
              <div class="health-label">MCP Servers</div>
              <el-tag type="info" size="large">{{ mcpServerCount }} Active</el-tag>
            </div>
            <div class="health-item">
              <div class="health-label">Tools Available</div>
              <el-tag type="info" size="large">{{ toolCount }} Tools</el-tag>
            </div>
            <div class="health-item">
              <div class="health-label">CPU Usage</div>
              <el-tag :type="cpuUsageTagType" size="large">{{ metrics.cpuUsage }}%</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Quick Actions & Recent Activity -->
    <el-row :gutter="20" class="actions-row">
      <el-col :xs="24" :sm="12" :md="12" :lg="12">
        <el-card class="actions-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>Quick Actions</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" :icon="ChatDotRound" @click="$router.push('/chat')">
              Open Chat
            </el-button>
            <el-button :icon="Refresh" @click="refreshMetrics" :loading="refreshing">
              Refresh Metrics
            </el-button>
            <el-button :icon="Setting" @click="openConfig">
              Configuration
            </el-button>
            <el-button type="warning" :icon="Delete" @click="clearAllSessions">
              Clear Sessions
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="12" :lg="12">
        <el-card class="activity-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>Recent Activity</span>
              <el-button link type="primary" size="small">View All</el-button>
            </div>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="activity in recentActivities"
              :key="activity.id"
              :timestamp="activity.timestamp"
              :type="activity.type"
            >
              {{ activity.message }}
            </el-timeline-item>
            <el-timeline-item v-if="recentActivities.length === 0" type="info">
              No recent activity
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  User,
  DataLine,
  Clock,
  Monitor,
  CaretTop,
  CaretBottom,
  TrendCharts,
  ChatDotRound,
  Refresh,
  Setting,
  Delete,
} from "@element-plus/icons-vue";
import { useAPI } from "../../services/api";

const api = useAPI();

// State
const metrics = ref({
  activeSessions: 0,
  totalEvents: 0,
  uptime: 0,
  memoryUsage: 0,
  cpuUsage: 0,
});

const sessionTrend = ref(0);
const eventRate = ref(0);
const startTime = ref("");
const chartTimeRange = ref("1h");
const refreshing = ref(false);
const mcpServerCount = ref(0);
const toolCount = ref(0);
const wsConnected = ref(true);

const recentActivities = ref<Array<{
  id: string;
  message: string;
  timestamp: string;
  type: "primary" | "success" | "warning" | "danger" | "info";
}>>([]);

let refreshInterval: number | null = null;
let previousSessionCount = 0;

// Computed
const memoryPercent = computed(() => {
  const maxMemory = 2048; // 2GB
  return Math.min((metrics.value.memoryUsage / maxMemory) * 100, 100);
});

const memoryColor = computed(() => {
  const percent = memoryPercent.value;
  if (percent < 50) return "#67c23a";
  if (percent < 80) return "#e6a23c";
  return "#f56c6c";
});

const cpuUsageTagType = computed(() => {
  const usage = metrics.value.cpuUsage;
  if (usage < 50) return "success";
  if (usage < 80) return "warning";
  return "danger";
});

// Methods
function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
  if (num >= 1000) return (num / 1000).toFixed(1) + "K";
  return num.toString();
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

async function refreshMetrics() {
  refreshing.value = true;

  try {
    const data = await api.getMetrics();

    // Calculate trends
    previousSessionCount = metrics.value.activeSessions;
    metrics.value = {
      activeSessions: data.active_sessions || 0,
      totalEvents: data.total_events || 0,
      uptime: data.uptime || 0,
      memoryUsage: data.memory_usage || 0,
      cpuUsage: data.cpu_usage || 0,
    };

    sessionTrend.value = metrics.value.activeSessions - previousSessionCount;

    // Calculate event rate (events per minute)
    eventRate.value = Math.floor((metrics.value.totalEvents / (metrics.value.uptime / 60)) || 0);

    // Set start time
    if (metrics.value.uptime > 0) {
      const startDate = new Date(Date.now() - metrics.value.uptime * 1000);
      startTime.value = startDate.toLocaleTimeString();
    }

    // Fetch additional data
    try {
      const mcpServers = await api.listMCPServers();
      mcpServerCount.value = mcpServers.length || 0;
    } catch (e) {
      mcpServerCount.value = 0;
    }

    try {
      const tools = await api.listTools();
      toolCount.value = tools.length || 0;
    } catch (e) {
      toolCount.value = 0;
    }

    // Add activity
    addActivity("Metrics refreshed", "info");

  } catch (error: any) {
    ElMessage.error(`Failed to refresh metrics: ${error.message}`);
    addActivity(`Metrics refresh failed: ${error.message}`, "danger");
  } finally {
    refreshing.value = false;
  }
}

function addActivity(message: string, type: "primary" | "success" | "warning" | "danger" | "info" = "info") {
  recentActivities.value.unshift({
    id: Date.now().toString(),
    message,
    timestamp: new Date().toLocaleTimeString(),
    type,
  });

  // Keep only last 5 activities
  if (recentActivities.value.length > 5) {
    recentActivities.value = recentActivities.value.slice(0, 5);
  }
}

async function clearAllSessions() {
  try {
    await ElMessageBox.confirm(
      "This will terminate all active sessions. Continue?",
      "Clear All Sessions",
      {
        confirmButtonText: "Clear",
        cancelButtonText: "Cancel",
        type: "warning",
      }
    );

    // Terminate all sessions
    const sessions = await api.listSessions();
    for (const session of sessions) {
      await api.terminateSession(session.session_id);
    }

    ElMessage.success("All sessions cleared");
    addActivity("All sessions terminated", "warning");
    refreshMetrics();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(`Failed to clear sessions: ${error.message}`);
    }
  }
}

function openConfig() {
  // Navigate to config or emit event to parent
  window.location.hash = "#config";
}

// Lifecycle
onMounted(() => {
  refreshMetrics();

  // Auto-refresh every 30 seconds
  refreshInterval = window.setInterval(() => {
    refreshMetrics();
  }, 30000);

  addActivity("Dashboard initialized", "success");
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Metrics Cards */
.metrics-row {
  margin-bottom: 0;
}

.metric-card {
  position: relative;
  transition: transform 0.2s, box-shadow 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
}

.metric-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.metric-icon.active-sessions {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.metric-icon.total-events {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.metric-icon.uptime {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.metric-icon.memory {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  color: white;
}

.metric-info {
  flex: 1;
}

.metric-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.metric-label {
  font-size: 0.875rem;
  color: var(--el-text-color-secondary);
  margin-top: 0.25rem;
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin-top: 0.5rem;
}

.metric-trend.positive {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

.metric-trend.negative {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

.metric-footer {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: var(--el-text-color-secondary);
}

.metric-progress {
  margin-top: 0.75rem;
}

/* Charts */
.charts-row {
  margin-bottom: 0;
}

.chart-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.chart-container {
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-placeholder {
  text-align: center;
  color: var(--el-text-color-secondary);
}

.chart-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.3;
}

.placeholder-text {
  font-size: 0.875rem;
  margin-top: 0.5rem;
  opacity: 0.7;
}

/* Health Status */
.health-status {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.health-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.health-label {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

/* Quick Actions */
.actions-row {
  margin-bottom: 0;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
}

.quick-actions .el-button {
  width: 100%;
}

/* Activity Timeline */
.activity-card {
  height: 100%;
}

.activity-card :deep(.el-timeline) {
  padding-left: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .metric-value {
    font-size: 1.5rem;
  }

  .metric-icon {
    width: 40px;
    height: 40px;
    font-size: 1.25rem;
  }

  .quick-actions {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
