<template>
  <div class="marketplace-view">
    <!-- Header -->
    <header class="marketplace-header">
      <div class="header-left">
        <h1>MCP Tool Marketplace</h1>
        <p>Discover and install Model Context Protocol servers</p>
      </div>
      <div class="header-right">
        <el-button @click="$router.push('/admin')" :icon="ArrowLeft">
          Back to Admin
        </el-button>
        <el-button @click="refreshRegistry" :icon="Refresh" :loading="refreshing">
          Refresh
        </el-button>
      </div>
    </header>

    <!-- Search and Filter Bar -->
    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        placeholder="Search tools..."
        prefix-icon="Search"
        size="large"
        clearable
        class="search-input"
        @input="handleSearch"
      >
        <template #append>
          <el-button :icon="Search" />
        </template>
      </el-input>

      <el-select
        v-model="selectedCategory"
        placeholder="All Categories"
        size="large"
        clearable
        class="category-select"
        @change="handleFilter"
      >
        <el-option label="All Categories" value="" />
        <el-option
          v-for="cat in categories"
          :key="cat.id"
          :label="cat.name"
          :value="cat.id"
        >
          <div class="category-option">
            <el-icon><component :is="cat.icon" /></el-icon>
            <span>{{ cat.name }}</span>
          </div>
        </el-option>
      </el-select>

      <el-radio-group v-model="sortOption" size="large" @change="handleSort">
        <el-radio-button label="popular">Popular</el-radio-button>
        <el-radio-button label="rating">Top Rated</el-radio-button>
        <el-radio-button label="new">New</el-radio-button>
        <el-radio-button label="name">Name</el-radio-button>
      </el-radio-group>
    </div>

    <!-- Quick Categories -->
    <div class="quick-categories" v-if="!searchQuery && !selectedCategory">
      <el-button
        v-for="cat in categories"
        :key="cat.id"
        :icon="cat.icon"
        @click="selectCategory(cat.id)"
        class="category-button"
      >
        {{ cat.name }}
        <el-badge :value="getCategoryCount(cat.id)" class="category-badge" />
      </el-button>
    </div>

    <!-- Installed Tools Section -->
    <div v-if="installedTools.length > 0 && !searchQuery && !selectedCategory" class="section">
      <div class="section-header">
        <h2>
          <el-icon><CircleCheck /></el-icon>
          Installed Tools ({{ installedTools.length }})
        </h2>
        <el-button link type="primary" @click="scrollToGrid('all')">
          View All Tools
        </el-button>
      </div>
      <el-row :gutter="20" class="tools-row">
        <el-col
          v-for="tool in installedTools"
          :key="tool.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <MarketplaceCard
            :tool="tool"
            :installed="true"
            @install="handleInstall"
            @uninstall="handleUninstall(tool)"
            @configure="handleConfigure(tool)"
          />
        </el-col>
      </el-row>
    </div>

    <!-- Featured Tools -->
    <div v-if="!searchQuery && !selectedCategory" class="section">
      <div class="section-header">
        <h2>
          <el-icon><Star /></el-icon>
          Featured Tools
        </h2>
        <el-button link type="primary" @click="scrollToGrid('all')">
          View All
        </el-button>
      </div>
      <el-row :gutter="20" class="tools-row">
        <el-col
          v-for="tool in featuredTools"
          :key="tool.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <MarketplaceCard
            :tool="tool"
            :installed="isToolInstalled(tool.id)"
            @install="handleInstall"
            @uninstall="handleUninstall(tool)"
            @configure="handleConfigure(tool)"
          />
        </el-col>
      </el-row>
    </div>

    <!-- All Tools Grid -->
    <div id="all-tools" class="section">
      <div class="section-header">
        <h2>
          <el-icon><Grid /></el-icon>
          All Tools
          <span class="count">({{ filteredTools.length }})</span>
        </h2>
        <div class="header-actions">
          <el-text v-if="selectedCategory" type="info">
            {{ getCategoryName(selectedCategory) }}
            <el-button link size="small" @click="clearCategory">
              <el-icon><Close /></el-icon>
              Clear
            </el-button>
          </el-text>
        </div>
      </div>

      <!-- Empty State -->
      <el-empty
        v-if="filteredTools.length === 0"
        description="No tools found"
        :image-size="200"
      >
        <el-button type="primary" @click="clearFilters">Clear Filters</el-button>
      </el-empty>

      <!-- Tools Grid -->
      <div v-else class="tools-grid-container">
        <el-row :gutter="20" class="tools-row">
          <el-col
            v-for="tool in paginatedTools"
            :key="tool.id"
            :xs="24"
            :sm="12"
            :md="8"
            :lg="6"
          >
            <MarketplaceCard
              :tool="tool"
              :installed="isToolInstalled(tool.id)"
              @install="handleInstall"
              @uninstall="handleUninstall(tool)"
              @configure="handleConfigure(tool)"
            />
          </el-col>
        </el-row>

        <!-- Pagination -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[12, 24, 48, 96]"
            :total="filteredTools.length"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>

    <!-- Installation History Dialog -->
    <el-dialog
      v-model="historyDialogVisible"
      title="Installation History"
      width="70%"
    >
      <el-timeline>
        <el-timeline-item
          v-for="(entry, index) in installHistory"
          :key="index"
          :timestamp="entry.timestamp"
          :type="entry.type"
          :icon="entry.type === 'success' ? CircleCheck : Close"
        >
          <el-card>
            <h4>{{ entry.toolName }}</h4>
            <p>{{ entry.message }}</p>
            <el-tag v-if="entry.status" :type="entry.status === 'success' ? 'success' : 'danger'">
              {{ entry.status }}
            </el-tag>
          </el-card>
        </el-timeline-item>
      </el-timeline>
      <template #footer>
        <el-button @click="clearHistory">Clear History</el-button>
        <el-button type="primary" @click="historyDialogVisible = false">Close</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
  ArrowLeft,
  Refresh,
  Search,
  Star,
  Grid,
  CircleCheck,
  Close,
} from "@element-plus/icons-vue";
import MarketplaceCard from "../components/mcp/MarketplaceCard.vue";
import { useConfigStore } from "../stores/config";
import { useSessionStore } from "../stores/session";

// Import tool registry
import toolRegistryData from "../data/mcp-tools.json";

const configStore = useConfigStore();
const sessionStore = useSessionStore();

// State
const searchQuery = ref("");
const selectedCategory = ref("");
const sortOption = ref("popular");
const currentPage = ref(1);
const pageSize = ref(12);
const refreshing = ref(false);
const historyDialogVisible = ref(false);

const categories = ref(toolRegistryData.categories);
const allTools = ref(toolRegistryData.tools);
const featuredToolIds = ref(toolRegistryData.featured_tools);
const popularToolIds = ref(toolRegistryData.popular_tools);
const newToolIds = ref(toolRegistryData.new_tools);

const installHistory = ref<Array<{
  toolName: string;
  message: string;
  timestamp: string;
  type: "success" | "danger";
  status?: string;
}>>([]);

// Computed
const installedTools = computed(() => {
  const installed = configStore.mcpServers || [];
  return allTools.value.filter((tool) => installed.includes(tool.id));
});

const featuredTools = computed(() => {
  return featuredToolIds.value
    .map((id) => allTools.value.find((t) => t.id === id))
    .filter(Boolean);
});

const filteredTools = computed(() => {
  let tools = allTools.value;

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    tools = tools.filter((tool) =>
      tool.name.toLowerCase().includes(query) ||
      tool.description.toLowerCase().includes(query) ||
      tool.tags.some((tag: string) => tag.toLowerCase().includes(query))
    );
  }

  // Filter by category
  if (selectedCategory.value) {
    tools = tools.filter((tool) => tool.category === selectedCategory.value);
  }

  // Sort
  switch (sortOption.value) {
    case "popular":
      tools = [...tools].sort((a, b) => b.stats.downloads - a.stats.downloads);
      break;
    case "rating":
      tools = [...tools].sort((a, b) => b.stats.rating - a.stats.rating);
      break;
    case "new":
      tools = [...tools].filter((t) => newToolIds.value.includes(t.id));
      break;
    case "name":
      tools = [...tools].sort((a, b) => a.name.localeCompare(b.name));
      break;
  }

  return tools;
});

const paginatedTools = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredTools.value.slice(start, end);
});

// Methods
function isToolInstalled(toolId: string): boolean {
  const installed = configStore.mcpServers || [];
  return installed.includes(toolId);
}

function getCategoryName(categoryId: string): string {
  const cat = categories.value.find((c) => c.id === categoryId);
  return cat?.name || categoryId;
}

function getCategoryCount(categoryId: string): number {
  return allTools.value.filter((t) => t.category === categoryId).length;
}

function selectCategory(categoryId: string) {
  selectedCategory.value = categoryId;
  handleFilter();
  scrollToGrid("all");
}

function clearCategory() {
  selectedCategory.value = "";
  handleFilter();
}

function clearFilters() {
  searchQuery.value = "";
  selectedCategory.value = "";
  handleFilter();
}

function handleSearch() {
  currentPage.value = 1;
}

function handleFilter() {
  currentPage.value = 1;
}

function handleSort() {
  currentPage.value = 1;
}

function handleSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
}

function handleCurrentChange(page: number) {
  currentPage.value = page;
  scrollToGrid("all");
}

function scrollToGrid(id: string) {
  const element = document.getElementById(id + "-tools");
  if (element) {
    element.scrollIntoView({ behavior: "smooth" });
  }
}

async function handleInstall(toolConfig: any) {
  try {
    // Add to config store
    configStore.addMCPServer(toolConfig.name, {
      command: toolConfig.command,
      args: toolConfig.args,
      env: toolConfig.env,
      enabled: true,
    });

    // Add to install history
    installHistory.value.unshift({
      toolName: toolConfig.name,
      message: `Successfully installed ${toolConfig.name}`,
      timestamp: new Date().toLocaleString(),
      type: "success",
      status: "success",
    });

    ElMessage.success(`${toolConfig.name} installed successfully`);

    // Refresh configuration
    await configStore.fetchConfig();
  } catch (error: any) {
    installHistory.value.unshift({
      toolName: toolConfig.name,
      message: `Failed to install: ${error.message}`,
      timestamp: new Date().toLocaleString(),
      type: "danger",
      status: "failed",
    });
    ElMessage.error(`Installation failed: ${error.message}`);
  }
}

async function handleUninstall(tool: any) {
  try {
    // Remove from config store
    configStore.removeMCPServer(tool.id);

    // Add to install history
    installHistory.value.unshift({
      toolName: tool.name,
      message: `Successfully removed ${tool.name}`,
      timestamp: new Date().toLocaleString(),
      type: "success",
      status: "removed",
    });

    ElMessage.success(`${tool.name} removed successfully`);

    // Refresh configuration
    await configStore.fetchConfig();
  } catch (error: any) {
    ElMessage.error(`Removal failed: ${error.message}`);
  }
}

function handleConfigure(tool: any) {
  // Navigate to config editor with tool selected
  window.location.hash = "#config";
  ElMessage.info(`Configure ${tool.name} in the Configuration tab`);
}

async function refreshRegistry() {
  refreshing.value = true;

  try {
    // Re-import registry (in production, would fetch from API)
    const updated = await import("../data/mcp-tools.json");
    allTools.value = updated.default.tools;
    categories.value = updated.default.categories;

    ElMessage.success("Tool registry refreshed");
  } catch (error: any) {
    ElMessage.error(`Failed to refresh: ${error.message}`);
  } finally {
    refreshing.value = false;
  }
}

function clearHistory() {
  installHistory.value = [];
  ElMessage.info("Installation history cleared");
}

// Lifecycle
onMounted(() => {
  // Load installed tools from config
  configStore.fetchConfig();
});
</script>

<style scoped>
.marketplace-view {
  min-height: 100vh;
  padding: 2rem;
  background: var(--el-bg-color-page);
}

/* Header */
.marketplace-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-left h1 {
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.header-left p {
  margin: 0;
  font-size: 1.125rem;
  color: var(--el-text-color-secondary);
}

.header-right {
  display: flex;
  gap: 0.75rem;
}

/* Search Bar */
.search-bar {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 300px;
}

.category-select {
  width: 200px;
}

.category-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Quick Categories */
.quick-categories {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 2rem;
  padding: 1rem;
  background: var(--el-bg-color);
  border-radius: 8px;
}

.category-button {
  position: relative;
}

.category-badge {
  margin-left: 0.5rem;
}

/* Sections */
.section {
  margin-bottom: 3rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.5rem;
  font-weight: 600;
}

.section-header .count {
  font-size: 1rem;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

/* Tools Grid */
.tools-row {
  margin-bottom: 0;
}

.tools-grid-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 2rem 0;
}

/* Responsive */
@media (max-width: 768px) {
  .marketplace-view {
    padding: 1rem;
  }

  .marketplace-header {
    flex-direction: column;
  }

  .header-right {
    width: 100%;
  }

  .header-right .el-button {
    flex: 1;
  }

  .search-bar {
    flex-direction: column;
  }

  .search-input,
  .category-select {
    width: 100%;
  }

  .quick-categories {
    flex-direction: column;
  }

  .category-button {
    width: 100%;
  }

  .section-header {
    flex-direction: column;
    gap: 0.75rem;
    align-items: flex-start;
  }
}
</style>
