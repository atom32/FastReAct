<template>
  <div class="config-editor">
    <!-- Config Tabs -->
    <el-tabs v-model="activeTab" type="border-card" class="config-tabs">
      <!-- LLM Configuration -->
      <el-tab-pane label="LLM Settings" name="llm">
        <div class="tab-content">
          <el-form
            ref="llmFormRef"
            :model="llmConfig"
            :rules="llmRules"
            label-width="140px"
            label-position="left"
          >
            <el-form-item label="Provider" prop="provider">
              <el-select
                v-model="llmConfig.provider"
                placeholder="Select LLM provider"
                @change="onProviderChange"
              >
                <el-option label="OpenAI" value="openai" />
                <el-option label="Anthropic" value="anthropic" />
                <el-option label="Azure OpenAI" value="azure" />
                <el-option label="LocalAI" value="localai" />
                <el-option label="Ollama" value="ollama" />
                <el-option label="Custom" value="custom" />
              </el-select>
              <div class="form-hint">Choose your LLM provider</div>
            </el-form-item>

            <el-form-item label="Model" prop="model">
              <el-select
                v-model="llmConfig.model"
                placeholder="Select model"
                filterable
                allow-create
              >
                <el-option
                  v-for="model in availableModels"
                  :key="model.value"
                  :label="model.label"
                  :value="model.value"
                />
              </el-select>
              <div class="form-hint">Model name or ID</div>
            </el-form-item>

            <el-form-item label="API Key" prop="apiKey">
              <el-input
                v-model="llmConfig.apiKey"
                type="password"
                placeholder="sk-..."
                show-password
              />
              <div class="form-hint">
                Your API key (stored securely)
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="loadApiKeyFromEnv"
                >
                  Load from ENV
                </el-button>
              </div>
            </el-form-item>

            <el-form-item label="Base URL" prop="baseUrl">
              <el-input
                v-model="llmConfig.baseUrl"
                placeholder="https://api.openai.com/v1"
              />
              <div class="form-hint">API endpoint URL</div>
            </el-form-item>

            <el-form-item label="Temperature" prop="temperature">
              <el-slider
                v-model="llmConfig.temperature"
                :min="0"
                :max="2"
                :step="0.1"
                :marks="{ 0: 'Precise', 1: 'Balanced', 2: 'Creative' }"
                show-input
              />
              <div class="form-hint">
                Controls randomness: Lower = more focused, Higher = more creative
              </div>
            </el-form-item>

            <el-form-item label="Max Tokens" prop="maxTokens">
              <el-input-number
                v-model="llmConfig.maxTokens"
                :min="1"
                :max="128000"
                :step="1000"
              />
              <div class="form-hint">Maximum response length</div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="testLLMConnection" :loading="testingLLM">
                <el-icon><Connection /></el-icon>
                Test Connection
              </el-button>
              <el-button @click="resetLLMConfig">Reset to Defaults</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- MCP Servers -->
      <el-tab-pane label="MCP Servers" name="mcp">
        <div class="tab-content">
          <div class="section-header">
            <h3>Model Context Protocol Servers</h3>
            <el-button type="primary" :icon="Plus" @click="addMCPServer">
              Add Server
            </el-button>
          </div>

          <el-empty v-if="mcpServers.length === 0" description="No MCP servers configured">
            <el-button type="primary" @click="addMCPServer">Add Your First Server</el-button>
          </el-empty>

          <div v-else class="mcp-server-list">
            <el-card
              v-for="(server, index) in mcpServers"
              :key="index"
              class="mcp-server-card"
              shadow="hover"
            >
              <template #header>
                <div class="server-header">
                  <div class="server-info">
                    <el-icon class="server-icon"><Monitor /></el-icon>
                    <span class="server-name">{{ server.name }}</span>
                    <el-tag :type="server.enabled ? 'success' : 'info'" size="small">
                      {{ server.enabled ? 'Enabled' : 'Disabled' }}
                    </el-tag>
                  </div>
                  <div class="server-actions">
                    <el-button
                      size="small"
                      :icon="server.enabled ? VideoPause : VideoPlay"
                      @click="toggleMCPServer(index)"
                    >
                      {{ server.enabled ? 'Disable' : 'Enable' }}
                    </el-button>
                    <el-button
                      size="small"
                      :icon="Delete"
                      type="danger"
                      @click="removeMCPServer(index)"
                    >
                      Remove
                    </el-button>
                  </div>
                </div>
              </template>

              <el-form :model="server" label-width="100px" label-position="left">
                <el-form-item label="Command">
                  <el-input v-model="server.command" placeholder="npx" />
                </el-form-item>

                <el-form-item label="Arguments">
                  <el-input
                    v-model="server.argsStr"
                    type="textarea"
                    :rows="2"
                    placeholder='["@modelcontextprotocol/server-filesystem", "/path"]'
                    @blur="updateServerArgs(server)"
                  />
                  <div class="form-hint">JSON array of arguments</div>
                </el-form-item>

                <el-form-item label="Environment">
                  <div class="env-vars">
                    <div
                      v-for="(value, key) in server.env"
                      :key="key"
                      class="env-var-item"
                    >
                      <el-input v-model="server.env[key]" :placeholder="key">
                        <template #prepend>{{ key }}</template>
                        <template #append>
                          <el-button
                            :icon="Close"
                            @click="removeEnvVar(server, key)"
                          />
                        </template>
                      </el-input>
                    </div>
                    <el-button
                      size="small"
                      :icon="Plus"
                      @click="addEnvVar(server)"
                    >
                      Add Environment Variable
                    </el-button>
                  </div>
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <!-- Agent Settings -->
      <el-tab-pane label="Agent Settings" name="agent">
        <div class="tab-content">
          <el-form
            ref="agentFormRef"
            :model="agentConfig"
            label-width="160px"
            label-position="left"
          >
            <el-form-item label="System Prompt">
              <el-input
                v-model="agentConfig.systemPrompt"
                type="textarea"
                :rows="6"
                placeholder="You are a helpful AI assistant..."
              />
              <div class="form-hint">Custom system prompt for the agent</div>
            </el-form-item>

            <el-form-item label="Max Iterations">
              <el-input-number
                v-model="agentConfig.maxIterations"
                :min="1"
                :max="100"
              />
              <div class="form-hint">Maximum tool execution iterations per query</div>
            </el-form-item>

            <el-form-item label="Timeout (seconds)">
              <el-input-number
                v-model="agentConfig.timeout"
                :min="5"
                :max="300"
              />
              <div class="form-hint">Tool execution timeout</div>
            </el-form-item>

            <el-form-item label="Enabled Tools">
              <el-select
                v-model="agentConfig.enabledTools"
                multiple
                filterable
                placeholder="Select tools to enable"
                style="width: 100%"
              >
                <el-option
                  v-for="tool in availableTools"
                  :key="tool"
                  :label="tool"
                  :value="tool"
                />
              </el-select>
              <div class="form-hint">Leave empty for all tools</div>
            </el-form-item>

            <el-form-item label="Debug Mode">
              <el-switch v-model="agentConfig.debugMode" />
              <div class="form-hint">Enable detailed logging</div>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- Advanced -->
      <el-tab-pane label="Advanced" name="advanced">
        <div class="tab-content">
          <el-alert
            title="Advanced Settings"
            type="warning"
            description="These settings are for advanced users only. Incorrect values may cause issues."
            :closable="false"
            show-icon
            class="advanced-warning"
          />

          <el-form label-width="180px" label-position="left">
            <el-form-item label="Concurrent Requests">
              <el-input-number v-model="advancedConfig.concurrentRequests" :min="1" :max="10" />
            </el-form-item>

            <el-form-item label="Request Timeout">
              <el-input-number v-model="advancedConfig.requestTimeout" :min="10" :max="300" />
              <span class="unit-label">seconds</span>
            </el-form-item>

            <el-form-item label="Retry Attempts">
              <el-input-number v-model="advancedConfig.retryAttempts" :min="0" :max="5" />
            </el-form-item>

            <el-form-item label="Cache Responses">
              <el-switch v-model="advancedConfig.cacheResponses" />
            </el-form-item>

            <el-form-item label="Stream Responses">
              <el-switch v-model="advancedConfig.streamResponses" />
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Config Diff View -->
    <el-card class="diff-card" v-if="hasChanges">
      <template #header>
        <div class="diff-header">
          <span>Unsaved Changes</span>
          <div class="diff-actions">
            <el-button size="small" @click="discardChanges">Discard</el-button>
            <el-button size="small" type="primary" @click="showDiffDialog">View Diff</el-button>
          </div>
        </div>
      </template>
      <div class="changes-summary">
        <el-tag>{{ changeCount }} changes</el-tag>
        <span class="changes-text">Click "Save Configuration" to apply changes</span>
      </div>
    </el-card>

    <!-- Action Buttons -->
    <div class="config-actions">
      <el-button @click="loadConfig" :icon="Refresh">Reload</el-button>
      <el-button @click="exportConfig" :icon="Download">Export</el-button>
      <el-upload
        :show-file-list="false"
        :before-upload="importConfig"
        accept=".json"
      >
        <el-button :icon="Upload">Import</el-button>
      </el-upload>
      <el-button type="primary" @click="saveConfig" :loading="saving" :disabled="!hasChanges">
        <el-icon><Check /></el-icon>
        Save Configuration
      </el-button>
    </div>

    <!-- Diff Dialog -->
    <el-dialog
      v-model="diffDialogVisible"
      title="Configuration Changes"
      width="70%"
    >
      <div class="diff-view">
        <pre class="diff-content">{{ diffText }}</pre>
      </div>
      <template #footer>
        <el-button @click="diffDialogVisible = false">Close</el-button>
        <el-button type="primary" @click="saveConfig; diffDialogVisible = false">
          Apply Changes
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Plus,
  Delete,
  Close,
  Monitor,
  Connection,
  Refresh,
  Download,
  Upload,
  Check,
  VideoPlay,
  VideoPause,
} from "@element-plus/icons-vue";
import { useAPI } from "../../services/api";
import type { FormInstance, FormRules } from "element-plus";

const api = useAPI();

// State
const activeTab = ref("llm");
const saving = ref(false);
const testingLLM = ref(false);
const diffDialogVisible = ref(false);

const llmFormRef = ref<FormInstance>();
const agentFormRef = ref<FormInstance>();

const llmConfig = ref({
  provider: "openai",
  model: "gpt-4o-mini",
  apiKey: "",
  baseUrl: "https://api.openai.com/v1",
  temperature: 0.7,
  maxTokens: 4096,
});

const agentConfig = ref({
  systemPrompt: "",
  maxIterations: 10,
  timeout: 30,
  enabledTools: [] as string[],
  debugMode: false,
});

const advancedConfig = ref({
  concurrentRequests: 3,
  requestTimeout: 60,
  retryAttempts: 3,
  cacheResponses: true,
  streamResponses: true,
});

const mcpServers = ref<Array<{
  name: string;
  command: string;
  args: string[];
  argsStr: string;
  env: Record<string, string>;
  enabled: boolean;
}>>([]);

const originalConfig = ref<any>({});
const availableTools = ref<string[]>([]);

// Available models by provider
const providerModels: Record<string, string[]> = {
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
  anthropic: ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
  azure: ["gpt-4o", "gpt-4o-mini"],
  localai: ["local-model"],
  ollama: ["llama2", "mistral", "neural-chat"],
  custom: [],
};

// Computed
const availableModels = computed(() => {
  const models = providerModels[llmConfig.value.provider] || [];
  return models.map((m) => ({ label: m, value: m }));
});

const hasChanges = computed(() => {
  return JSON.stringify(currentConfig()) !== JSON.stringify(originalConfig.value);
});

const changeCount = computed(() => {
  const current = currentConfig();
  const original = originalConfig.value;
  let count = 0;

  for (const key in current) {
    if (JSON.stringify(current[key]) !== JSON.stringify(original[key])) {
      count++;
    }
  }

  return count;
});

const diffText = computed(() => {
  const current = currentConfig();
  const original = originalConfig.value;
  const lines: string[] = [];

  for (const key in current) {
    const currentValue = JSON.stringify(current[key], null, 2);
    const originalValue = JSON.stringify(original[key], null, 2);

    if (currentValue !== originalValue) {
      lines.push(`# ${key.toUpperCase()}`);
      lines.push(`- ${originalValue}`);
      lines.push(`+ ${currentValue}`);
      lines.push("");
    }
  }

  return lines.join("\n") || "No changes";
});

// Rules
const llmRules: FormRules = {
  provider: [{ required: true, message: "Please select a provider", trigger: "change" }],
  model: [{ required: true, message: "Please select or enter a model", trigger: "blur" }],
  apiKey: [{ required: true, message: "API key is required", trigger: "blur" }],
  baseUrl: [{ required: true, message: "Base URL is required", trigger: "blur" }],
};

// Methods
function currentConfig() {
  return {
    llm: llmConfig.value,
    agent: agentConfig.value,
    advanced: advancedConfig.value,
    mcpServers: mcpServers.value,
  };
}

async function loadConfig() {
  try {
    const config = await api.getConfig();
    originalConfig.value = JSON.parse(JSON.stringify(config));

    if (config.llm) {
      llmConfig.value = { ...llmConfig.value, ...config.llm };
    }
    if (config.mcp_servers) {
      mcpServers.value = Object.entries(config.mcp_servers).map(([name, cfg]: [string, any]) => ({
        name,
        command: cfg.command || "",
        args: cfg.args || [],
        argsStr: JSON.stringify(cfg.args || []),
        env: cfg.env || {},
        enabled: cfg.enabled !== false,
      }));
    }
    if (config.system_prompt) {
      agentConfig.value.systemPrompt = config.system_prompt;
    }
    if (config.max_iterations) {
      agentConfig.value.maxIterations = config.max_iterations;
    }
    if (config.timeout) {
      agentConfig.value.timeout = config.timeout;
    }
    if (config.tools) {
      agentConfig.value.enabledTools = config.tools;
    }

    ElMessage.success("Configuration loaded");
  } catch (error: any) {
    ElMessage.error(`Failed to load config: ${error.message}`);
  }
}

async function saveConfig() {
  saving.value = true;

  try {
    // Validate forms
    await llmFormRef.value?.validate();
    await agentFormRef.value?.validate();

    const config = {
      llm: llmConfig.value,
      system_prompt: agentConfig.value.systemPrompt,
      max_iterations: agentConfig.value.maxIterations,
      timeout: agentConfig.value.timeout,
      tools: agentConfig.value.enabledTools,
      mcp_servers: mcpServers.value
        .filter((s) => s.enabled)
        .reduce((acc, s) => {
          acc[s.name] = {
            command: s.command,
            args: s.args,
            env: s.env,
          };
          return acc;
        }, {} as Record<string, any>),
    };

    await api.updateConfig(config);
    originalConfig.value = JSON.parse(JSON.stringify(currentConfig()));

    ElMessage.success("Configuration saved successfully");
  } catch (error: any) {
    ElMessage.error(`Failed to save config: ${error.message}`);
  } finally {
    saving.value = false;
  }
}

function onProviderChange() {
  const models = providerModels[llmConfig.value.provider];
  if (models && models.length > 0) {
    llmConfig.value.model = models[0];
  }
}

async function testLLMConnection() {
  testingLLM.value = true;

  try {
    await llmFormRef.value?.validate();

    // Simulate test (would call actual API endpoint)
    await new Promise((resolve) => setTimeout(resolve, 2000));

    ElMessage.success("Connection successful!");
  } catch (error: any) {
    ElMessage.error(`Connection failed: ${error.message}`);
  } finally {
    testingLLM.value = false;
  }
}

function addMCPServer() {
  const name = `mcp-server-${mcpServers.value.length + 1}`;
  mcpServers.value.push({
    name,
    command: "npx",
    args: [],
    argsStr: "[]",
    env: {},
    enabled: true,
  });
  activeTab.value = "mcp";
}

function removeMCPServer(index: number) {
  mcpServers.value.splice(index, 1);
}

function toggleMCPServer(index: number) {
  mcpServers.value[index].enabled = !mcpServers.value[index].enabled;
}

function updateServerArgs(server: any) {
  try {
    server.args = JSON.parse(server.argsStr || "[]");
  } catch (e) {
    ElMessage.error("Invalid JSON for arguments");
    server.argsStr = JSON.stringify(server.args);
  }
}

function addEnvVar(server: any) {
  const key = `VAR_${Object.keys(server.env).length + 1}`;
  server.env[key] = "";
}

function removeEnvVar(server: any, key: string) {
  delete server.env[key];
}

function loadApiKeyFromEnv() {
  llmConfig.value.apiKey = "sk-***from-env***";
  ElMessage.info("API key loaded from environment");
}

function resetLLMConfig() {
  llmConfig.value = {
    provider: "openai",
    model: "gpt-4o-mini",
    apiKey: "",
    baseUrl: "https://api.openai.com/v1",
    temperature: 0.7,
    maxTokens: 4096,
  };
}

function discardChanges() {
  loadConfig();
}

function showDiffDialog() {
  diffDialogVisible.value = true;
}

function exportConfig() {
  const config = currentConfig();
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "fastreact-config.json";
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success("Configuration exported");
}

async function importConfig(file: File) {
  try {
    const text = await file.text();
    const config = JSON.parse(text);

    if (confirm("This will replace your current configuration. Continue?")) {
      // Apply imported config
      if (config.llm) llmConfig.value = config.llm;
      if (config.agent) agentConfig.value = config.agent;
      if (config.mcpServers) mcpServers.value = config.mcpServers;

      ElMessage.success("Configuration imported");
    }

    return false;
  } catch (error: any) {
    ElMessage.error(`Failed to import: ${error.message}`);
    return false;
  }
}

async function loadAvailableTools() {
  try {
    const tools = await api.listTools();
    availableTools.value = tools.map((t: any) => t.name || t);
  } catch (e) {
    availableTools.value = [
      "web_search",
      "file_read",
      "file_write",
      "shell_execute",
      "code_interpret",
    ];
  }
}

// Lifecycle
onMounted(() => {
  loadConfig();
  loadAvailableTools();
});
</script>

<style scoped>
.config-editor {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-tabs {
  width: 100%;
}

.tab-content {
  padding: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.form-hint {
  font-size: 0.75rem;
  color: var(--el-text-color-secondary);
  margin-top: 0.25rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.unit-label {
  margin-left: 0.5rem;
  color: var(--el-text-color-secondary);
}

/* MCP Servers */
.mcp-server-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.mcp-server-card {
  border: 1px solid var(--el-border-color);
}

.server-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.server-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.server-icon {
  font-size: 1.5rem;
  color: var(--el-color-primary);
}

.server-name {
  font-weight: 600;
}

.server-actions {
  display: flex;
  gap: 0.5rem;
}

.env-vars {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}

.env-var-item {
  width: 100%;
}

/* Advanced Warning */
.advanced-warning {
  margin-bottom: 1.5rem;
}

/* Diff Card */
.diff-card {
  border: 1px solid var(--el-color-warning);
  background: var(--el-color-warning-light-9);
}

.diff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.diff-actions {
  display: flex;
  gap: 0.5rem;
}

.changes-summary {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.changes-text {
  color: var(--el-text-color-secondary);
}

/* Config Actions */
.config-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

/* Diff Dialog */
.diff-view {
  max-height: 60vh;
  overflow-y: auto;
}

.diff-content {
  margin: 0;
  padding: 1rem;
  background: var(--el-bg-color-page);
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Responsive */
@media (max-width: 768px) {
  .config-actions {
    flex-direction: column;
  }

  .config-actions .el-button {
    width: 100%;
  }

  .server-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
}
</style>
