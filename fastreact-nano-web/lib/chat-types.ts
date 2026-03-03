export type EventType = "session_start" | "think" | "tool_call" | "tool_result" | "ask_user" | "session_end" | "text"

export interface ChatEvent {
  id: string
  type: EventType
  content: string
  toolName?: string
  toolArgs?: Record<string, any>
  metadata?: Record<string, any>
  timestamp: number
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  events?: ChatEvent[]
  timestamp: number
  skills?: string[]  // SKILLs used for this message
}

export type ConnectionStatus = "connected" | "connecting" | "disconnected"
