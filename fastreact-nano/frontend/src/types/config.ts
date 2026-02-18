/**
 * Configuration types
 */

export interface LLMConfig {
  provider: string;
  model: string;
  api_key?: string;
  base_url?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface MCPServerConfig {
  name: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
  enabled?: boolean;
}

export interface AgentConfig {
  llm: LLMConfig;
  mcp_servers?: Record<string, MCPServerConfig>;
  tools?: string[];
  system_prompt?: string;
  max_iterations?: number;
  timeout?: number;
}

export interface ConfigValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ConfigDiff {
  path: string;
  oldValue: any;
  newValue: any;
}
