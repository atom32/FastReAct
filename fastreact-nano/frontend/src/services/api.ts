/**
 * REST API client for Gateway
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:9000";

export class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API Error: ${response.status} - ${error}`);
    }

    return response.json();
  }

  // === Config ===
  async getConfig(): Promise<any> {
    return this.request("/api/config");
  }

  async updateConfig(config: any): Promise<void> {
    return this.request("/api/config", {
      method: "PUT",
      body: JSON.stringify(config),
    });
  }

  // === Sessions ===
  async listSessions(): Promise<any[]> {
    return this.request("/api/sessions");
  }

  async getSession(sessionId: string): Promise<any> {
    return this.request(`/api/sessions/${sessionId}`);
  }

  async terminateSession(sessionId: string): Promise<void> {
    return this.request(`/api/sessions/${sessionId}`, {
      method: "DELETE",
    });
  }

  async getSessionHistory(sessionId: string): Promise<any> {
    return this.request(`/api/sessions/${sessionId}/history`);
  }

  // === Tools ===
  async listTools(): Promise<any[]> {
    return this.request("/api/tools");
  }

  async testTool(toolName: string, parameters: any): Promise<any> {
    return this.request("/api/tools/test", {
      method: "POST",
      body: JSON.stringify({ tool_name: toolName, parameters }),
    });
  }

  // === MCP Servers ===
  async listMCPServers(): Promise<any[]> {
    return this.request("/api/mcp/servers");
  }

  async addMCPServer(config: any): Promise<void> {
    return this.request("/api/mcp/servers", {
      method: "POST",
      body: JSON.stringify(config),
    });
  }

  async removeMCPServer(name: string): Promise<void> {
    return this.request(`/api/mcp/servers/${name}`, {
      method: "DELETE",
    });
  }

  async restartMCPServer(name: string): Promise<void> {
    return this.request(`/api/mcp/servers/${name}/restart`, {
      method: "POST",
    });
  }

  // === Metrics ===
  async getMetrics(): Promise<any> {
    return this.request("/api/metrics");
  }

  // === Health ===
  async healthCheck(): Promise<{ status: string; version: string }> {
    return this.request("/health");
  }
}

// Global API client instance
let globalAPIClient: APIClient | null = null;

export function useAPI() {
  if (!globalAPIClient) {
    globalAPIClient = new APIClient();
  }

  return globalAPIClient;
}
