/**
 * Configuration state management
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { AgentConfig } from "../types/config";

export const useConfigStore = defineStore("config", () => {
  // State
  const config = ref<AgentConfig | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const dirty = ref(false);

  // Computed
  const llmProvider = computed(() => config.value?.llm?.provider || "");
  const llmModel = computed(() => config.value?.llm?.model || "");
  const mcpServers = computed(() => Object.keys(config.value?.mcp_servers || {}));
  const enabledTools = computed(() => config.value?.tools || []);

  // Actions
  async function fetchConfig() {
    loading.value = true;
    error.value = null;

    try {
      // Will be implemented with API client
      // const api = useAPI();
      // config.value = await api.getConfig();
    } catch (e: any) {
      error.value = e.message;
      console.error("Failed to fetch config:", e);
    } finally {
      loading.value = false;
    }
  }

  function updateConfig(newConfig: Partial<AgentConfig>) {
    if (config.value) {
      config.value = { ...config.value, ...newConfig };
      dirty.value = true;
    }
  }

  function updateLLMConfig(llmConfig: Partial<AgentConfig["llm"]>) {
    if (config.value) {
      config.value.llm = { ...config.value.llm, ...llmConfig };
      dirty.value = true;
    }
  }

  function addMCPServer(name: string, serverConfig: any) {
    if (config.value) {
      if (!config.value.mcp_servers) {
        config.value.mcp_servers = {};
      }
      config.value.mcp_servers[name] = serverConfig;
      dirty.value = true;
    }
  }

  function removeMCPServer(name: string) {
    if (config.value?.mcp_servers) {
      delete config.value.mcp_servers[name];
      dirty.value = true;
    }
  }

  function markDirty() {
    dirty.value = true;
  }

  function markClean() {
    dirty.value = false;
  }

  return {
    // State
    config,
    loading,
    error,
    dirty,

    // Computed
    llmProvider,
    llmModel,
    mcpServers,
    enabledTools,

    // Actions
    fetchConfig,
    updateConfig,
    updateLLMConfig,
    addMCPServer,
    removeMCPServer,
    markDirty,
    markClean,
  };
});
