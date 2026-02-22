"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Square } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ChatInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  statusLabel?: string
  isProcessing?: boolean
}

export function ChatInput({ onSend, onStop, statusLabel, isProcessing }: ChatInputProps) {
  const [value, setValue] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + "px"
    }
  }, [value])

  const handleSubmit = () => {
    const trimmed = value.trim()
    if (!trimmed) return
    onSend(trimmed)
    setValue("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Ctrl+Enter or Cmd+Enter to send (standard behavior)
    // Enter alone creates a new line
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div
      className="glass-panel sticky bottom-0 z-40 px-4 pb-5 pt-3 sm:px-6"
      style={{
        borderTop: `1px solid var(--fr-border-glow)`,
      }}
    >
      {/* Status badge */}
      {statusLabel && (
        <div className="mb-2 flex justify-center">
          <div
            className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium"
            style={{
              background: `rgba(139, 92, 246, 0.15)`,
              border: `1px solid var(--fr-border-glow)`,
              color: "var(--fr-accent-primary)",
            }}
          >
            {statusLabel}
          </div>
        </div>
      )}

      <div className="mx-auto flex max-w-[900px] items-end gap-3">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Send a message... (Ctrl+Enter to send)"
            rows={1}
            className="block w-full resize-none rounded-xl px-4 py-3.5 text-sm outline-none transition-all duration-300 placeholder:opacity-50"
            style={{
              background: "var(--fr-bg-primary)",
              border: `2px solid var(--fr-border-glow)`,
              color: "var(--fr-text-primary)",
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "var(--fr-accent-primary)"
              e.currentTarget.style.boxShadow = `0 0 20px var(--fr-border-glow)`
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = `var(--fr-border-glow)`
              e.currentTarget.style.boxShadow = "none"
            }}
          />
        </div>

        {isProcessing && onStop ? (
          <button
            onClick={onStop}
            className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-white transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0"
            style={{
              background: "#ef4444",
              boxShadow: "0 4px 15px rgba(239, 68, 68, 0.4)",
            }}
            title="Stop Agent"
          >
            <Square className="h-4 w-4" />
            <span>Stop</span>
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={!value.trim()}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-white transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-40 disabled:hover:translate-y-0"
            style={{
              background: `linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))`,
              boxShadow: value.trim()
                ? `0 4px 15px var(--fr-border-glow)`
                : "none",
            }}
            aria-label="Send message"
          >
            <Send className="h-5 w-5" />
          </button>
        )}
      </div>

      <p
        className="mt-2 text-center text-[11px]"
        style={{ color: "var(--fr-text-muted)" }}
      >
        {"FastReAct Nano can make mistakes. Verify important information."}
      </p>
    </div>
  )
}
