/**
 * API response types
 */

export interface APISession {
  session_id: string;
  created_at: string;
  last_active: string;
  status: "active" | "idle" | "terminated";
  event_count: number;
  config?: Record<string, any>;
}

export interface APITool {
  name: string;
  description: string;
  parameters: Record<string, any>;
  mcp_server?: string;
}

export interface MCPServerInfo {
  name: string;
  status: "connected" | "disconnected" | "error";
  tools: string[];
  config: Record<string, any>;
}

export interface SystemMetrics {
  active_sessions: number;
  total_events: number;
  uptime: number;
  memory_usage: number;
  cpu_usage: number;
}

export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface SessionHistory {
  session_id: string;
  events: any[];
  created_at: string;
  ended_at?: string;
}
