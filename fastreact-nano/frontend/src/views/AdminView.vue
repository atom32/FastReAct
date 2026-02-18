<template>
  <div class="admin-view">
    <!-- Admin Header -->
    <header class="admin-header">
      <div class="header-left">
        <h1>Admin Panel</h1>
        <el-tag type="info" size="small">FastReAct Nano v2.0</el-tag>
      </div>
      <div class="header-right">
        <el-button @click="$router.push('/marketplace')" :icon="ShoppingBag">
          Tool Marketplace
        </el-button>
        <el-button @click="$router.push('/chat')" :icon="ChatDotRound">
          Open Chat
        </el-button>
        <el-button @click="toggleTheme" :icon="isDark ? Sunny : Moon" circle />
      </div>
    </header>

    <!-- Admin Navigation -->
    <nav class="admin-nav">
      <el-menu
        :default-active="activeSection"
        mode="horizontal"
        @select="onSectionSelect"
        class="admin-menu"
      >
        <el-menu-item index="dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>
        <el-menu-item index="sessions">
          <el-icon><List /></el-icon>
          <span>Sessions</span>
          <el-badge v-if="activeSessionCount > 0" :value="activeSessionCount" class="nav-badge" />
        </el-menu-item>
        <el-menu-item index="config">
          <el-icon><Setting /></el-icon>
          <span>Configuration</span>
        </el-menu-item>
      </el-menu>
    </nav>

    <!-- Admin Content -->
    <main class="admin-content">
      <!-- Dashboard Section -->
      <div v-show="activeSection === 'dashboard'" class="content-section">
        <Dashboard />
      </div>

      <!-- Sessions Section -->
      <div v-show="activeSection === 'sessions'" class="content-section">
        <SessionManager />
      </div>

      <!-- Config Section -->
      <div v-show="activeSection === 'config'" class="content-section">
        <ConfigEditor />
      </div>
    </main>

    <!-- Status Bar -->
    <footer class="admin-footer">
      <div class="footer-left">
        <el-tag :type="wsConnected ? 'success' : 'danger'" size="small">
          <el-icon><Connection v-if="wsConnected" /><Close v-else /></el-icon>
          {{ wsConnected ? 'Connected' : 'Disconnected' }}
        </el-tag>
        <span class="footer-text">Last sync: {{ lastSyncTime }}</span>
      </div>
      <div class="footer-right">
        <span class="footer-text">Active Sessions: {{ activeSessionCount }}</span>
        <el-divider direction="vertical" />
        <span class="footer-text">Uptime: {{ formattedUptime }}</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import {
  ChatDotRound,
  Sunny,
  Moon,
  DataBoard,
  List,
  Setting,
  Connection,
  Close,
  ShoppingBag,
} from "@element-plus/icons-vue";
import { useTheme } from "../composables/useTheme";
import { useSessionStore } from "../stores/session";
import { useWebSocket } from "../services/websocket";
import Dashboard from "../components/admin/Dashboard.vue";
import SessionManager from "../components/admin/SessionManager.vue";
import ConfigEditor from "../components/admin/ConfigEditor.vue";

const { isDark, toggleTheme } = useTheme();
const sessionStore = useSessionStore();
const { status: wsStatus } = useWebSocket();

// State
const activeSection = ref("dashboard");
const lastSyncTime = ref(new Date().toLocaleTimeString());
const startTime = ref(Date.now());
let syncInterval: number | null = null;

// Computed
const wsConnected = computed(() => wsStatus.value === "connected");
const activeSessionCount = computed(() => sessionStore.sessionCount);

const formattedUptime = computed(() => {
  const elapsed = Math.floor((Date.now() - startTime.value) / 1000);
  const hours = Math.floor(elapsed / 3600);
  const minutes = Math.floor((elapsed % 3600) / 60);
  const seconds = elapsed % 60;

  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
});

// Methods
function onSectionSelect(index: string) {
  activeSection.value = index;
  ElMessage.success(`Switched to ${index.charAt(0).toUpperCase() + index.slice(1)}`);
}

function updateSyncTime() {
  lastSyncTime.value = new Date().toLocaleTimeString();
}

// Lifecycle
onMounted(() => {
  updateSyncTime();
  syncInterval = window.setInterval(updateSyncTime, 30000);
  ElMessage.success("Admin panel loaded");
});

onUnmounted(() => {
  if (syncInterval) {
    clearInterval(syncInterval);
  }
});
</script>

<style scoped>
.admin-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--el-bg-color-page);
}

/* Header */
.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-left h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 0.75rem;
}

/* Navigation */
.admin-nav {
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
}

.admin-menu {
  padding: 0 2rem;
  border-bottom: none;
}

.nav-badge {
  margin-left: 0.5rem;
}

/* Content */
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.content-section {
  height: 100%;
}

/* Footer */
.admin-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 2rem;
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color);
}

.footer-left,
.footer-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.footer-text {
  font-size: 0.875rem;
  color: var(--el-text-color-secondary);
}

/* Responsive */
@media (max-width: 768px) {
  .admin-header {
    padding: 1rem;
  }

  .admin-menu {
    padding: 0 1rem;
  }

  .admin-content {
    padding: 1rem;
  }

  .admin-footer {
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
  }

  .footer-left,
  .footer-right {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
  }
}
</style>
