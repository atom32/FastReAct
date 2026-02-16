"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import type { ChatEvent, ConnectionStatus } from "@/lib/chat-types"

const GATEWAY_URL = "ws://localhost:9000/ws"
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

export function useFastReActWS({
  onEvent,
  onUserMessage,
  onConfirmationRequired,
  onStatusChange,
  onError,
}: UseFastReActWSOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)
  const errorShownRef = useRef(false)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5
  const isConnectingRef = useRef(false)

  // Use refs to store callbacks and avoid recreating WebSocket
  const onEventRef = useRef(onEvent)
  const onUserMessageRef = useRef(onUserMessage)
  const onConfirmationRequiredRef = useRef(onConfirmationRequired)
  const onStatusChangeRef = useRef(onStatusChange)
  const onErrorRef = useRef(onError)

  // Update refs when callbacks change
  useEffect(() => {
    onEventRef.current = onEvent
    onUserMessageRef.current = onUserMessage
    onConfirmationRequiredRef.current = onConfirmationRequired
    onStatusChangeRef.current = onStatusChange
    onErrorRef.current = onError
  })

  const [status, setStatus] = useState<ConnectionStatus>("disconnected")

  // WebSocket connection - only run once on mount
  useEffect(() => {
    const mountId = Math.random().toString(36).substring(2, 8)

    log(`Setting up connection (mount: ${mountId})`)

    const connectInternal = () => {
      log(`connectInternal called (mount: ${mountId})`)

      // Prevent duplicate connection attempts
      if (isConnectingRef.current) {
        log("Already connecting, skipping duplicate attempt")
        return
      }

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        log("Already connected, skipping")
        return
      }

      log("Connecting to", GATEWAY_URL)
      onStatusChangeRef.current?.("connecting")
      setStatus("connecting")
      isConnectingRef.current = true

      try {
        const ws = new WebSocket(GATEWAY_URL)
        const connectionSuccessfulRef = { current: false }
        wsRef.current = ws

        ws.onopen = () => {
          log("onopen fired - connection established")
          onStatusChangeRef.current?.("connected")
          setStatus("connected")
          reconnectAttempts.current = 0
          errorShownRef.current = false
          connectionSuccessfulRef.current = true
          isConnectingRef.current = false
          log("connectionSuccessfulRef set to true, isConnectingRef cleared")
        }

        ws.onmessage = (event) => {
          try {
            const data: WebSocketMessage = JSON.parse(event.data)
            log("Received:", data)

            if (data.type === "connected") {
              log("Server confirmed connection:", data.session_id)
              connectionSuccessfulRef.current = true
            } else if (data.type === "user") {
              onUserMessageRef.current?.(data.content || "")
            } else if (data.type === "event") {
              const chatEvent: ChatEvent = {
                id: Math.random().toString(36).substring(2, 12),
                type: (data.event_type || "text") as any,
                content: data.content || "",
                toolName: data.tool_name,
                timestamp: Date.now(),
              }
              onEventRef.current?.(chatEvent)
            } else if (data.type === "user_input_required") {
              onConfirmationRequiredRef.current?.({
                reason: data.reason || "",
                tool_name: data.tool_name || "",
                tool_args: data.tool_args || {},
              })
            } else if (data.type === "error") {
              onErrorRef.current?.(data.content || "Unknown error")
            }
          } catch (err) {
            logError("Failed to parse message:", err)
          }
        }

        ws.onclose = (event) => {
          log("onclose fired - code:", event.code, "reason:", event.reason)
          log("connectionSuccessfulRef was:", connectionSuccessfulRef.current)
          onStatusChangeRef.current?.("disconnected")
          setStatus("disconnected")
          wsRef.current = null
          isConnectingRef.current = false

          // Show error only if connection was never successful
          if (!connectionSuccessfulRef.current && !errorShownRef.current) {
            log("Connection failed - showing error to user")
            errorShownRef.current = true
            onErrorRef.current?.("Failed to connect to Gateway")
          } else {
            log("Connection was successful, no error shown")
          }

          // Attempt to reconnect
          if (reconnectAttempts.current < maxReconnectAttempts) {
            reconnectAttempts.current++
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
            log(`Reconnecting in ${delay}ms`)

            reconnectTimeoutRef.current = setTimeout(() => {
              connectInternal()
            }, delay)
          } else {
            logError("Max reconnection attempts reached")
            if (!errorShownRef.current) {
              errorShownRef.current = true
              onErrorRef.current?.("Connection lost. Please refresh the page.")
            }
          }
        }

        ws.onerror = (error) => {
          logError("Error event:", error)
          // Don't show error - wait for onclose to determine if connection failed
        }
      } catch (err) {
        logError("Connection failed:", err)
        isConnectingRef.current = false
        onStatusChangeRef.current?.("disconnected")
        setStatus("disconnected")
        onErrorRef.current?.("Failed to connect to Gateway")
      }
    }

    // Initial connection
    connectInternal()

    // Cleanup
    return () => {
      log(`Cleanup called for mount ${mountId}, readyState:`, wsRef.current?.readyState, "isConnecting:", isConnectingRef.current)

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        log("Cleared reconnect timeout")
      }

      // Only close if connection is actually open
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        log("Closing active WebSocket connection in cleanup")
        wsRef.current.close()
        wsRef.current = null
      } else if (wsRef.current) {
        console.log("[WebSocket] WebSocket not OPEN, skipping close")
        wsRef.current = null
      }

      isConnectingRef.current = false
    }
  }, []) // Empty deps - only run once on mount

  const send = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = {
        type: "query",
        content: content,
      }
      wsRef.current.send(JSON.stringify(message))
      console.log("[WebSocket] Sent:", message)
    } else {
      onErrorRef.current?.("Not connected to Gateway")
    }
  }, [])

  const sendUserResponse = useCallback((approved: boolean, reason?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const response = approved ? "yes" : `${reason || "Denied"}`
      const message: WebSocketMessage = {
        type: "query",
        content: response,
      }
      wsRef.current.send(JSON.stringify(message))
      console.log("[WebSocket] Sent user response:", message)
    }
  }, [])

  const connect = useCallback(() => {
    console.log("[WebSocket] connect() called - connection is auto-managed")
  }, [])

  const disconnect = useCallback(() => {
    console.log("[WebSocket] disconnect() called")
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus("disconnected")
    onStatusChangeRef.current?.("disconnected")
  }, [])

  return {
    status,
    send,
    sendUserResponse,
    connect,
    disconnect,
  }
}
