<template>
  <el-card class="marketplace-card" shadow="hover" :class="{ installed: isInstalled }">
    <!-- Card Header -->
    <template #header>
      <div class="card-header">
        <div class="tool-info">
          <div class="tool-icon" :style="{ backgroundColor: iconColor }">
            <el-icon size="24">
              <component :is="tool.icon" />
            </el-icon>
          </div>
          <div class="tool-meta">
            <h3 class="tool-name">{{ tool.name }}</h3>
            <div class="tool-author">{{ tool.author }}</div>
          </div>
        </div>
        <el-tag v-if="isInstalled" type="success" size="small">
          <el-icon><CircleCheck /></el-icon>
          Installed
        </el-tag>
        <el-tag v-else-if="isNew" type="danger" size="small">
          NEW
        </el-tag>
      </div>
    </template>

    <!-- Card Content -->
    <div class="card-content">
      <!-- Description -->
      <p class="tool-description">{{ tool.description }}</p>

      <!-- Stats -->
      <div class="tool-stats">
        <div class="stat-item">
          <el-rate
            v-model="tool.stats.rating"
            disabled
            show-score
            text-color="#ff9900"
            score-template="{value}"
          />
        </div>
        <div class="stat-item">
          <el-icon><Download /></el-icon>
          <span>{{ formatNumber(tool.stats.downloads) }}</span>
        </div>
        <div class="stat-item">
          <el-icon><User /></el-icon>
          <span>{{ tool.stats.reviews }} reviews</span>
        </div>
      </div>

      <!-- Tags -->
      <div class="tool-tags">
        <el-tag
          v-for="tag in tool.tags.slice(0, 4)"
          :key="tag"
          size="small"
          class="tag-item"
        >
          {{ tag }}
        </el-tag>
      </div>

      <!-- Features Preview -->
      <el-collapse v-if="showFeatures" class="features-collapse">
        <el-collapse-item>
          <template #title>
            <span class="features-title">Features ({{ tool.features.length }})</span>
          </template>
          <ul class="features-list">
            <li v-for="(feature, index) in tool.features" :key="index">
              <el-icon><Check /></el-icon>
              <span>{{ feature }}</span>
            </li>
          </ul>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- Card Actions -->
    <template #footer>
      <div class="card-footer">
        <div class="footer-left">
          <el-button
            link
            type="primary"
            size="small"
            @click="showDetails = !showDetails"
          >
            {{ showDetails ? 'Less' : 'More' }} Details
          </el-button>
          <el-button
            v-if="tool.homepage"
            link
            type="info"
            size="small"
            @click="openHomepage"
          >
            <el-icon><Link /></el-icon>
            Docs
          </el-button>
        </div>
        <div class="footer-right">
          <el-button
            v-if="!isInstalled"
            type="primary"
            :icon="Plus"
            @click="handleInstall"
            :loading="installing"
          >
            Install
          </el-button>
          <el-button
            v-else
            type="danger"
            :icon="Delete"
            @click="handleUninstall"
            :loading="uninstalling"
          >
            Remove
          </el-button>
          <el-button
            v-if="isInstalled"
            :icon="Setting"
            @click="handleConfigure"
            circle
          />
        </div>
      </div>
    </template>

    <!-- Details Dialog -->
    <el-dialog
      v-model="showDetails"
      :title="tool.name"
      width="70%"
      destroy-on-close
    >
      <div class="tool-details">
        <!-- Overview -->
        <div class="detail-section">
          <h4>Overview</h4>
          <p>{{ tool.long_description }}</p>
        </div>

        <!-- Installation Info -->
        <div class="detail-section">
          <h4>Installation</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="Command">
              <code>{{ tool.installation.command }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="Arguments">
              <code>{{ JSON.stringify(tool.installation.args) }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="Config Required">
              <el-tag :type="tool.installation.config_required ? 'warning' : 'success'" size="small">
                {{ tool.installation.config_required ? 'Yes' : 'No' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="tool.installation.env" label="Environment">
              <div v-for="(value, key) in tool.installation.env" :key="key" class="env-item">
                <code>{{ key }}=***</code>
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- Tools Provided -->
        <div class="detail-section">
          <h4>Tools Provided ({{ tool.tools_provided.length }})</h4>
          <div class="tools-grid">
            <el-tag
              v-for="t in tool.tools_provided"
              :key="t.name"
              class="tool-tag"
              size="large"
            >
              <div class="tool-tag-content">
                <span class="tool-tag-name">{{ t.name }}</span>
                <span class="tool-tag-desc">{{ t.description }}</span>
              </div>
            </el-tag>
          </div>
        </div>

        <!-- Features -->
        <div class="detail-section">
          <h4>Features</h4>
          <ul class="features-list">
            <li v-for="(feature, index) in tool.features" :key="index">
              <el-icon><Check /></el-icon>
              <span>{{ feature }}</span>
            </li>
          </ul>
        </div>

        <!-- Requirements -->
        <div class="detail-section">
          <h4>Requirements</h4>
          <ul class="requirements-list">
            <li v-for="(req, index) in tool.requirements" :key="index">
              <el-icon><Warning /></el-icon>
              <span>{{ req }}</span>
            </li>
          </ul>
        </div>

        <!-- Stats -->
        <div class="detail-section">
          <h4>Statistics</h4>
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-box">
                <div class="stat-value">{{ formatNumber(tool.stats.downloads) }}</div>
                <div class="stat-label">Downloads</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-box">
                <div class="stat-value">{{ tool.stats.rating }}</div>
                <div class="stat-label">Rating</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-box">
                <div class="stat-value">{{ tool.stats.reviews }}</div>
                <div class="stat-label">Reviews</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-box">
                <div class="stat-value">{{ formatNumber(tool.stats.installs) }}</div>
                <div class="stat-label">Active Installs</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- Changelog -->
        <div v-if="tool.changelog && tool.changelog.length > 0" class="detail-section">
          <h4>Changelog</h4>
          <el-timeline>
            <el-timeline-item
              v-for="(entry, index) in tool.changelog"
              :key="index"
              :timestamp="entry.date"
              placement="top"
            >
              <el-card>
                <h5>v{{ entry.version }}</h5>
                <ul>
                  <li v-for="(change, i) in entry.changes" :key="i">{{ change }}</li>
                </ul>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>

        <!-- Links -->
        <div class="detail-section">
          <h4>Links</h4>
          <div class="links-section">
            <el-button
              v-if="tool.repository"
              type="primary"
              :icon="Link"
              @click="openRepository"
            >
              Repository
            </el-button>
            <el-button
              v-if="tool.homepage"
              type="default"
              :icon="Document"
              @click="openHomepage"
            >
              Documentation
            </el-button>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showDetails = false">Close</el-button>
        <el-button
          v-if="!isInstalled"
          type="primary"
          :icon="Plus"
          @click="handleInstall; showDetails = false"
          :loading="installing"
        >
          Install Tool
        </el-button>
      </template>
    </el-dialog>

    <!-- Config Dialog -->
    <el-dialog
      v-model="showConfig"
      title="Configure Tool"
      width="600px"
      destroy-on-close
    >
      <div class="config-dialog">
        <el-alert
          v-if="tool.installation.config_required"
          title="Configuration Required"
          type="warning"
          :description="`This tool requires configuration before use. Please provide the following ${Object.keys(tool.installation.config_schema || {}).length} parameters.`"
          :closable="false"
          show-icon
          class="config-alert"
        />

        <el-form :model="configForm" label-width="140px">
          <el-form-item
            v-for="(schema, key) in tool.installation.config_schema"
            :key="key"
            :label="formatLabel(key)"
            :required="schema.required"
          >
            <el-input
              v-if="schema.type === 'string' && !key.includes('secret') && !key.includes('password') && !key.includes('key')"
              v-model="configForm[key]"
              :placeholder="schema.example || ''"
            />
            <el-input
              v-else
              v-model="configForm[key]"
              type="password"
              :placeholder="schema.example || ''"
              show-password
            />
            <div class="form-hint">{{ schema.description }}</div>
          </el-form-item>

          <!-- Environment Variables -->
          <el-form-item v-if="tool.installation.env" label="Environment">
            <div class="env-config">
              <div
                v-for="(value, key) in tool.installation.env"
                :key="key"
                class="env-item-config"
              >
                <el-input
                  v-model="envForm[key]"
                  :placeholder="key"
                  show-password
                >
                  <template #prepend>{{ key }}</template>
                </el-input>
              </div>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="showConfig = false">Cancel</el-button>
        <el-button type="primary" @click="handleSaveConfig" :loading="saving">
          Save & Install
        </el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Plus,
  Delete,
  Setting,
  Download,
  User,
  Link,
  Check,
  Warning,
  Document,
  CircleCheck,
} from "@element-plus/icons-vue";

// Props
const props = defineProps<{
  tool: any;
  installed?: boolean;
}>();

// Emits
const emit = defineEmits<{
  install: [config: any];
  uninstall: [];
  configure: [];
}>();

// State
const showDetails = ref(false);
const showConfig = ref(false);
const installing = ref(false);
const uninstalling = ref(false);
const saving = ref(false);

const configForm = ref<Record<string, string>>({});
const envForm = ref<Record<string, string>>({});
const showFeatures = ref(false);

// Computed
const isInstalled = computed(() => props.installed);

const isNew = computed(() => {
  // Check if tool is in the "new_tools" list from registry
  return false; // Would be determined by parent
});

const iconColor = computed(() => {
  const colors: Record<string, string> = {
    Filesystem: "#67C23A",
    Git: "#F56C6C",
    Database: "#409EFF",
    Communication: "#E6A23C",
    Development: "#909399",
    Productivity: "#9C27B0",
    "AI & ML": "#E91E63",
    Web: "#2196F3",
    Cloud: "#00BCD4",
  };
  return colors[props.tool.category] || "#606266";
});

// Methods
function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
  if (num >= 1000) return (num / 1000).toFixed(1) + "K";
  return num.toString();
}

function formatLabel(key: string): string {
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

async function handleInstall() {
  if (props.tool.installation.config_required || Object.keys(props.tool.installation.env || {}).length > 0) {
    // Show config dialog
    showConfig.value = true;

    // Initialize form with defaults
    if (props.tool.installation.config_schema) {
      Object.keys(props.tool.installation.config_schema).forEach((key) => {
        configForm.value[key] = "";
      });
    }

    if (props.tool.installation.env) {
      Object.keys(props.tool.installation.env).forEach((key) => {
        envForm.value[key] = "";
      });
    }
  } else {
    // Install directly
    await doInstall({});
  }
}

async function doInstall(config: any) {
  installing.value = true;

  try {
    const installConfig = {
      tool: props.tool.id,
      name: props.tool.name,
      command: props.tool.installation.command,
      args: props.tool.installation.args,
      env: { ...props.tool.installation.env, ...config.env },
      config: config.schema,
      enabled: true,
    };

    emit("install", installConfig);
    ElMessage.success(`${props.tool.name} installed successfully`);
    showConfig.value = false;
  } catch (error: any) {
    ElMessage.error(`Installation failed: ${error.message}`);
  } finally {
    installing.value = false;
  }
}

async function handleSaveConfig() {
  saving.value = true;

  try {
    // Merge config form and env form
    const config = {
      schema: configForm.value,
      env: envForm.value,
    };

    await doInstall(config);
  } catch (error: any) {
    ElMessage.error(`Failed to save config: ${error.message}`);
  } finally {
    saving.value = false;
  }
}

async function handleUninstall() {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to remove ${props.tool.name}?`,
      "Uninstall Tool",
      {
        confirmButtonText: "Remove",
        cancelButtonText: "Cancel",
        type: "warning",
      }
    );

    uninstalling.value = true;
    emit("uninstall");
    ElMessage.success(`${props.tool.name} removed successfully`);
  } catch (error) {
    // User cancelled
  } finally {
    uninstalling.value = false;
  }
}

function handleConfigure() {
  emit("configure");
}

function openHomepage() {
  if (props.tool.homepage) {
    window.open(props.tool.homepage, "_blank");
  }
}

function openRepository() {
  if (props.tool.repository) {
    window.open(props.tool.repository, "_blank");
  }
}
</script>

<style scoped>
.marketplace-card {
  height: 100%;
  transition: all 0.3s;
}

.marketplace-card:hover {
  transform: translateY(-4px);
}

.marketplace-card.installed {
  border-color: var(--el-color-success);
}

/* Card Header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.tool-info {
  display: flex;
  gap: 0.75rem;
  flex: 1;
}

.tool-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.tool-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.tool-name {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.tool-author {
  font-size: 0.875rem;
  color: var(--el-text-color-secondary);
}

/* Card Content */
.card-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tool-description {
  margin: 0;
  font-size: 0.875rem;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tool-stats {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: var(--el-text-color-secondary);
}

.tool-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag-item {
  font-size: 0.75rem;
}

.features-collapse {
  margin-top: 0.5rem;
}

.features-title {
  font-weight: 500;
}

.features-list {
  margin: 0;
  padding-left: 1.25rem;
  list-style: none;
}

.features-list li {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.features-list li .el-icon {
  color: var(--el-color-success);
  flex-shrink: 0;
}

/* Card Footer */
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-left {
  display: flex;
  gap: 0.5rem;
}

.footer-right {
  display: flex;
  gap: 0.5rem;
}

/* Details Dialog */
.tool-details {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.detail-section h4 {
  margin: 0 0 1rem 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--el-text-color-primary);
  border-bottom: 1px solid var(--el-border-color);
  padding-bottom: 0.5rem;
}

.detail-section p {
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.env-item {
  margin-bottom: 0.5rem;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 0.75rem;
}

.tool-tag {
  height: auto;
  padding: 0.75rem;
}

.tool-tag-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  text-align: left;
}

.tool-tag-name {
  font-weight: 600;
}

.tool-tag-desc {
  font-size: 0.75rem;
  opacity: 0.8;
}

.requirements-list {
  margin: 0;
  padding-left: 1.25rem;
  list-style: none;
}

.requirements-list li {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  color: var(--el-text-color-regular);
}

.requirements-list li .el-icon {
  color: var(--el-color-warning);
  flex-shrink: 0;
}

.stat-box {
  text-align: center;
  padding: 1rem;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--el-color-primary);
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--el-text-color-secondary);
}

.links-section {
  display: flex;
  gap: 0.75rem;
}

/* Config Dialog */
.config-dialog {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-alert {
  margin-bottom: 0;
}

.form-hint {
  font-size: 0.75rem;
  color: var(--el-text-color-secondary);
  margin-top: 0.25rem;
}

.env-config {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

.env-item-config {
  width: 100%;
}

/* Responsive */
@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    gap: 0.75rem;
  }

  .tool-stats {
    flex-wrap: wrap;
  }

  .card-footer {
    flex-direction: column;
    gap: 0.75rem;
  }

  .footer-left,
  .footer-right {
    width: 100%;
    justify-content: center;
  }

  .tools-grid {
    grid-template-columns: 1fr;
  }
}
</style>
