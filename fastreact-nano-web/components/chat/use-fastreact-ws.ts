"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import type { ChatEvent, ConnectionStatus } from "@/lib/chat-types"

// 自动检测：如果是局域网访问，使用本机 IP；否则用 localhost
const GATEWAY_URL = typeof window !== 'undefined'
  ? `ws://${window.location.hostname}:9000/ws`
  : "ws://localhost:9000/ws"

const isDev = process.env.NODE_ENV === 'development'

// Development-only logging utility
const log = isDev
  ? (...args: any[]) => console.log('[WebSocket]', ...args)
  : () => {}

const logError = (...args: any[]) => console.error('[WebSocket]', ...args)

interface WebSocketMessage {
  type: string
  content?: string
  event_type?: string
  tool_name?: string
  tool_args?: Record<string, any>
  session_id?: string
  metadata?: Record<string, any>
  reason?: string
}

interface UseFastReActWSOptions {
  onEvent?: (event: ChatEvent) => void
  onUserMessage?: (content: string) => void
  onConfirmationRequired?: (data: {
    reason: string
    tool_name: string
    tool_args: Record<string, any>
  }) => void
  onStatusChange?: (status: ConnectionStatus) => void
  onError?: (error: string) => void
}

// Global WebSocket manager singleton
class WebSocketManager {
  private static instance: WebSocketManager | null = null
  private ws: WebSocket | null = null
  private subscribers: Set<(msg: WebSocketMessage) => void> = new Set()
  private statusSubscribers: Set<(status: ConnectionStatus) => void> = new Set()
  private reconnectTimeout: NodeJS.Timeout | undefined
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private isConnecting = false

  private constructor() {}

  static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      WebSocketManager.instance = new WebSocketManager()
    }
    return WebSocketManager.instance
  }

  subscribe(callback: (msg: WebSocketMessage) => void) {
    this.subscribers.add(callback)
    return () => this.subscribers.delete(callback)
  }

  subscribeStatus(callback: (status: ConnectionStatus) => void) {
    this.statusSubscribers.add(callback)
    // Return current status immediately
    if (this.ws?.readyState === WebSocket.OPEN) {
      callback("connected")
    } else if (this.isConnecting) {
      callback("connecting")
    } else {
      callback("disconnected")
    }
    return () => this.statusSubscribers.delete(callback)
  }

  private notifyStatus(status: ConnectionStatus) {
    this.statusSubscribers.forEach(cb => cb(status))
  }

  private notify(message: WebSocketMessage) {
    this.subscribers.forEach(cb => cb(message))
  }

  connect() {
    if (this.isConnecting || (this.ws?.readyState === WebSocket.OPEN)) {
      return
    }

    this.isConnecting = true
    this.notifyStatus("connecting")
    log("Connecting to", GATEWAY_URL)

    try {
      this.ws = new WebSocket(GATEWAY_URL)

      this.ws.onopen = () => {
        log("Connection established")
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.notifyStatus("connected")
      }

      this.ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data)
          log("Received:", data)
          this.notify(data)
        } catch (error) {
          logError("Failed to parse message:", error)
        }
      }

      this.ws.onclose = (event) => {
        log("Connection closed:", event.code, event.reason)
        this.isConnecting = false
        this.notifyStatus("disconnected")
        this.ws = null

        // Reconnect logic
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
          log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`)

          this.reconnectTimeout = setTimeout(() => {
            this.reconnectAttempts++
            this.connect()
          }, delay)
        }
      }

      this.ws.onerror = (error) => {
        logError("WebSocket error:", error)
        this.notifyStatus("error")
      }
    } catch (error) {
      logError("Failed to create WebSocket:", error)
      this.isConnecting = false
      this.notifyStatus("error")
    }
  }

  send(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      log("Sent:", message)
    } else {
      logError("Cannot send message, WebSocket not connected")
    }
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.isConnecting = false
    this.reconnectAttempts = 0
  }
}

export function useFastReActWS({
  onEvent,
  onUserMessage,
  onConfirmationRequired,
  onStatusChange,
  onError,
}: UseFastReActWSOptions) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected")

  // Use refs to store callbacks and avoid recreating subscriptions
  const onEventRef = useRef(onEvent)
  const onUserMessageRef = useRef(onUserMessage)
  const onConfirmationRequiredRef = useRef(onConfirmationRequired)
  const onErrorRef = useRef(onError)

  // Update refs when callbacks change
  useEffect(() => {
    onEventRef.current = onEvent
    onUserMessageRef.current = onUserMessage
    onConfirmationRequiredRef.current = onConfirmationRequired
    onErrorRef.current = onError
  })

  // Connect to WebSocket manager
  useEffect(() => {
    const manager = WebSocketManager.getInstance()

    // Subscribe to messages
    const unsubscribe = manager.subscribe((message: WebSocketMessage) => {
      if (message.type === "event" && onEventRef.current) {
        onEventRef.current({
          id: Math.random().toString(36).substring(2, 12),
          type: message.event_type as any,
          content: message.content || "",
          toolName: message.tool_name,
          toolArgs: message.tool_args,
          metadata: message.metadata,
          timestamp: Date.now(),
        })
      } else if (message.type === "user_message" && onUserMessageRef.current) {
        onUserMessageRef.current(message.content || "")
      } else if (message.type === "confirmation_required" && onConfirmationRequiredRef.current) {
        onConfirmationRequiredRef.current({
          reason: message.reason || "",
          tool_name: message.tool_name || "",
          tool_args: message.tool_args || {},
        })
      } else if (message.type === "error" && onErrorRef.current) {
        onErrorRef.current(message.content || "Unknown error")
      }
    })

    // Subscribe to status changes
    const unsubscribeStatus = manager.subscribeStatus((newStatus) => {
      setStatus(newStatus)
      onStatusChange?.(newStatus)
    })

    // Connect if not already connected
    manager.connect()

    return () => {
      unsubscribe()
      unsubscribeStatus()
    }
  }, [])

  const sendMessage = useCallback((content: string) => {
    const manager = WebSocketManager.getInstance()
    manager.send({ type: "query", content })
  }, [])

  const stopAgent = useCallback(() => {
    const manager = WebSocketManager.getInstance()
    manager.send({
      type: "control",
      action: "interrupt",
      reason: "User cancelled"
    })
  }, [])

  return {
    status,
    sendMessage,
    stopAgent,
  }
}
