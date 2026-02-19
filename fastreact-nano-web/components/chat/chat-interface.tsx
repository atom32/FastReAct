"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import type { ChatMessage, ConnectionStatus, ChatEvent } from "@/lib/chat-types"
import { ChatHeader } from "./chat-header"
import { ChatMessageBubble } from "./chat-message"
import { ChatInput } from "./chat-input"
import { ThemePalette } from "./theme-palette"
import { ConfirmationModal } from "./confirmation-modal"
import { WelcomeScreen } from "./welcome-screen"
import { useFastReActWS } from "./use-fastreact-ws"

function generateId() {
  return Math.random().toString(36).substring(2, 12)
}

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [statusLabel, setStatusLabel] = useState("")
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected")
  const [isPaletteOpen, setIsPaletteOpen] = useState(false)
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean
    title: string
    description: string
  }>({ isOpen: false, title: "", description: "" })

  const scrollRef = useRef<HTMLDivElement>(null)
  const currentAssistantIdRef = useRef<string | null>(null)

  // Create refs for setState functions to avoid dependency issues
  const setMessagesRef = useRef(setMessages)
  const setConfirmModalRef = useRef(setConfirmModal)
  const setStatusLabelRef = useRef(setStatusLabel)

  // Update refs when setState functions change
  useEffect(() => {
    setMessagesRef.current = setMessages
    setConfirmModalRef.current = setConfirmModal
    setStatusLabelRef.current = setStatusLabel
  })

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      })
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Stable callback refs to prevent infinite reconnects
  const onEventCallback = useCallback((event: ChatEvent) => {
    // Update status label based on event type
    if (event.type === "session_start") {
      // Extract SKILLs from metadata and store in message
      const skills = event.metadata?.skills || []
      if (currentAssistantIdRef.current && skills.length > 0) {
        setMessagesRef.current((prev) =>
          prev.map((m) =>
            m.id === currentAssistantIdRef.current
              ? { ...m, skills }
              : m
          )
        )
      }
      setStatusLabelRef.current("")  // Don't show status for session_start
    }
    else if (event.type === "think") setStatusLabelRef.current("Thinking...")
    else if (event.type === "tool_call") setStatusLabelRef.current("Running tool...")
    else if (event.type === "tool_result") setStatusLabelRef.current("Processing result...")
    else if (event.type === "ask_user") setStatusLabelRef.current("Awaiting your response...")
    else if (event.type === "session_end") {
      setStatusLabelRef.current("")
    }
    else setStatusLabelRef.current("Processing...")

    // If it's an ask_user event, show the modal
    if (event.type === "ask_user") {
      setConfirmModalRef.current({
        isOpen: true,
        title: "Confirmation Required",
        description: event.content,
      })
    }

    // Add event to the current assistant message (but not session_end and session_start)
    if (currentAssistantIdRef.current && event.type !== "session_end" && event.type !== "session_start") {
      setMessagesRef.current((prev) =>
        prev.map((m) =>
          m.id === currentAssistantIdRef.current
            ? {
                ...m,
                events: [...(m.events || []), {
                  id: generateId(),
                  type: event.type,
                  content: event.content,
                  toolName: event.toolName,
                  metadata: event.metadata,
                  timestamp: event.timestamp || Date.now(),
                }],
              }
            : m
        )
      )
    }
  }, [])

  const onUserMessageCallback = useCallback((content: string) => {
    setMessagesRef.current((prev) => {
      // Check if the last message is already the same user message (avoid duplicates)
      const lastMessage = prev[prev.length - 1]
      if (lastMessage && lastMessage.role === "user" && lastMessage.content === content) {
        // Message already exists, skip adding duplicate
        return prev
      }

      // Add new user message
      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content,
        timestamp: Date.now(),
      }
      return [...prev, userMessage]
    })
  }, [])

  const onConfirmationRequiredCallback = useCallback((data: {
    reason: string
    tool_name: string
    tool_args: Record<string, any>
  }) => {
    setConfirmModalRef.current({
      isOpen: true,
      title: "Confirmation Required",
      description: `${data.reason}\n\nTool: ${data.tool_name}`,
    })
  }, [])

  const onStatusChangeCallback = useCallback((newStatus: ConnectionStatus) => {
    setConnectionStatus(newStatus)
  }, [])

  const onErrorCallback = useCallback((error: string) => {
    console.error("[Error]", error)
    setStatusLabelRef.current(error)
    // Show error as a system message
    const errorMessage: ChatMessage = {
      id: generateId(),
      role: "assistant",
      content: `[ERROR] ${error}`,
      timestamp: Date.now(),
    }
    setMessagesRef.current((prev) => [...prev, errorMessage])
  }, [])

  const { sendMessage, stopAgent, status } = useFastReActWS({
    onEvent: onEventCallback,
    onUserMessage: onUserMessageCallback,
    onConfirmationRequired: onConfirmationRequiredCallback,
    onStatusChange: onStatusChangeCallback,
    onError: onErrorCallback,
  })

  const [isProcessing, setIsProcessing] = useState(false)

  // Update processing state based on status label
  useEffect(() => {
    setIsProcessing(statusLabel !== "")
  }, [statusLabel])

  const handleSend = useCallback(
    (content: string) => {
      // First, add user message to maintain correct order
      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content,
        timestamp: Date.now(),
      }

      // Create assistant message placeholder
      const assistantId = generateId()
      currentAssistantIdRef.current = assistantId

      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        events: [],
        timestamp: Date.now(),
      }

      // Add both messages in correct order: user first, then assistant
      setMessages((prev) => [...prev, userMessage, assistantMessage])

      // Send to WebSocket
      sendMessage(content)
    },
    [sendMessage]
  )

  const handleStop = useCallback(() => {
    stopAgent()
    setStatusLabel("")
  }, [stopAgent])

  const handleConfirmApprove = useCallback(() => {
    setConfirmModal({ isOpen: false, title: "", description: "" })
  }, [])

  const handleConfirmDeny = useCallback(() => {
    setConfirmModal({ isOpen: false, title: "", description: "" })
  }, [])

  return (
    <div
      className="relative flex flex-col"
      style={{
        zIndex: 1,
        background: "var(--fr-bg-primary)",
        minHeight: "100vh",
      }}
    >
      {/* Background Mesh */}
      <div className="background-mesh" />

      {/* Chat Header (compact - no logo since it's in the navigation bar) */}
      <ChatHeader
        status={connectionStatus}
        onToggleThemePalette={() => setIsPaletteOpen((v) => !v)}
        compact={true}
      />

      <ThemePalette isOpen={isPaletteOpen} onClose={() => setIsPaletteOpen(false)} />

      {/* Messages area */}
      <div
        ref={scrollRef}
        className="custom-scrollbar flex-1 overflow-y-auto"
      >
        <div className="mx-auto max-w-[900px]">
          {messages.length === 0 ? (
            <WelcomeScreen onSuggestion={handleSend} />
          ) : (
            <div className="flex flex-col gap-5 px-4 py-6 sm:px-6">
              {messages.map((msg) => (
                <ChatMessageBubble key={msg.id} message={msg} />
              ))}
            </div>
          )}
        </div>
      </div>

      <ChatInput
        onSend={handleSend}
        onStop={handleStop}
        statusLabel={statusLabel}
        isProcessing={isProcessing}
      />

      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        description={confirmModal.description}
        onApprove={handleConfirmApprove}
        onDeny={handleConfirmDeny}
      />
    </div>
  )
}

