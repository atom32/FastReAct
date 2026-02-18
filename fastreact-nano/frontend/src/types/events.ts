/**
 * AgentEvent types matching the backend protocol
 */

export enum EventType {
  THINK = "think",
  TOOL_CALL = "tool_call",
  TOOL_RESULT = "tool_result",
  ERROR = "error",
  SESSION_START = "session_start",
  SESSION_END = "session_end",
  MESSAGE = "message",
}

export interface BaseEvent {
  type: EventType;
  timestamp: string;
  content?: string;
}

export interface ThinkEvent extends BaseEvent {
  type: EventType.THINK;
  content: string;
}

export interface ToolCallEvent extends BaseEvent {
  type: EventType.TOOL_CALL;
  tool_name: string;
  parameters: Record<string, any>;
  tool_id?: string;
}

export interface ToolResultEvent extends BaseEvent {
  type: EventType.TOOL_RESULT;
  tool_id: string;
  result: string;
  error?: string;
}

export interface ErrorEvent extends BaseEvent {
  type: EventType.ERROR;
  error: string;
  details?: string;
}

export interface SessionStartEvent extends BaseEvent {
  type: EventType.SESSION_START;
  session_id: string;
  config?: Record<string, any>;
}

export interface SessionEndEvent extends BaseEvent {
  type: EventType.SESSION_END;
  session_id: string;
  summary?: string;
}

export interface MessageEvent extends BaseEvent {
  type: EventType.MESSAGE;
  role: "user" | "assistant" | "system";
  content: string;
}

export type AgentEvent =
  | ThinkEvent
  | ToolCallEvent
  | ToolResultEvent
  | ErrorEvent
  | SessionStartEvent
  | SessionEndEvent
  | MessageEvent;

export interface WebSocketMessage {
  type: "event" | "query" | "response";
  data?: AgentEvent;
  query?: string;
  session_id?: string;
  error?: string;
}
