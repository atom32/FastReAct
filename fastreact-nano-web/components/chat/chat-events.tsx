"use client"

import { useState } from "react"
import { Brain, Wrench, FileText, AlertTriangle, ChevronDown, ChevronUp, Zap, User } from "lucide-react"
import type { ChatEvent } from "@/lib/chat-types"

function InterventionEvent({ event }: { event: ChatEvent }) {
  return (
    <div
      className="animate-slide-up my-2 flex gap-2.5 rounded-xl px-4 py-3"
      style={{
        background: `linear-gradient(90deg, rgba(139, 92, 246, 0.15), rgba(168, 85, 247, 0.15))`,
        border: `2px solid var(--fr-accent-primary)`,
        boxShadow: `0 0 15px rgba(139, 92, 246, 0.2)`,
      }}
    >
      <User className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--fr-accent-primary)" }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span
            className="rounded-full px-2 py-0.5 text-xs font-bold"
            style={{
              background: "var(--fr-accent-primary)",
              color: "white",
            }}
          >
            USER INTERVENTION
          </span>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: "var(--fr-text-primary)" }}>
          {event.content}
        </p>
      </div>
    </div>
  )
}

function ThinkEvent({ event }: { event: ChatEvent }) {
  // Don't show empty think events
  if (!event.content || event.content.trim() === "" || event.content === "\n\n") {
    return null
  }

  return (
    <div
      className="animate-slide-up my-1.5 flex gap-2.5 rounded-lg px-3 py-2.5"
      style={{
        background: `linear-gradient(90deg, rgba(139, 92, 246, 0.08), rgba(6, 182, 212, 0.08))`,
        borderLeft: "3px solid var(--fr-accent-primary)",
      }}
    >
      <Brain className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--fr-accent-primary)" }} />
      <p className="text-sm italic leading-relaxed" style={{ color: "var(--fr-accent-tertiary)" }}>
        {event.content}
        <span
          className="ml-0.5 inline-block h-3.5 w-0.5 animate-typing-cursor align-middle"
          style={{ background: "var(--fr-accent-primary)" }}
        />
      </p>
    </div>
  )
}

function ToolCallEvent({ event }: { event: ChatEvent }) {
  const toolName = event.toolName || "tool_call"
  const isMCP = toolName.includes("_") && !toolName.startsWith("read_") && !toolName.startsWith("write_") && !toolName.startsWith("edit_") && toolName !== "exec"

  return (
    <div
      className="animate-slide-up my-1.5 flex gap-2.5 rounded-lg px-3 py-2.5"
      style={{
        background: `linear-gradient(90deg, rgba(244, 114, 182, 0.1), rgba(251, 146, 60, 0.1))`,
        borderLeft: "3px solid var(--fr-accent-tertiary)",
      }}
    >
      <Wrench className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--fr-accent-tertiary)" }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold" style={{ color: "var(--fr-accent-tertiary)" }}>
            {toolName}
          </span>
          {isMCP && (
            <span
              className="rounded-full px-2 py-0.5 text-xs font-medium"
              style={{
                background: "rgba(139, 92, 246, 0.15)",
                color: "var(--fr-accent-primary)",
              }}
            >
              MCP
            </span>
          )}
        </div>
        {event.content && event.content.trim() && (
          <p className="mt-1 font-mono text-xs leading-relaxed" style={{ color: "var(--fr-text-secondary)" }}>
            {event.content}
          </p>
        )}
      </div>
    </div>
  )
}

function ToolResultEvent({ event }: { event: ChatEvent }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = event.content.length > 200

  return (
    <div
      className="animate-slide-up my-1.5 flex gap-2.5 rounded-lg px-3 py-2.5"
      style={{
        background: `linear-gradient(90deg, rgba(16, 185, 129, 0.06), rgba(52, 211, 153, 0.06))`,
        borderLeft: "3px solid var(--fr-success)",
      }}
    >
      <FileText className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--fr-success)" }} />
      <div className="min-w-0 flex-1">
        <pre
          className="whitespace-pre-wrap font-mono text-xs leading-relaxed"
          style={{
            color: "var(--fr-text-secondary)",
            maxHeight: expanded ? "none" : "120px",
            overflow: "hidden",
          }}
        >
          {event.content}
        </pre>
        {isLong && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-1.5 flex items-center gap-1 text-xs font-medium transition-colors"
            style={{ color: "var(--fr-success)" }}
          >
            {expanded ? (
              <>
                <ChevronUp className="h-3 w-3" /> Show less
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3" /> Show more
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}

function AskUserEvent({ event }: { event: ChatEvent }) {
  return (
    <div
      className="animate-slide-up animate-pulse-glow my-2 flex gap-2.5 rounded-xl px-4 py-3"
      style={{
        background: `linear-gradient(90deg, rgba(251, 191, 36, 0.1), rgba(254, 215, 170, 0.1))`,
        border: `2px solid var(--fr-warning)`,
        boxShadow: `0 0 15px rgba(251, 191, 36, 0.15)`,
      }}
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--fr-warning)" }} />
      <p className="text-sm font-medium leading-relaxed" style={{ color: "var(--fr-warning)" }}>
        {event.content}
      </p>
    </div>
  )
}

function ErrorEvent({ event }: { event: ChatEvent }) {
  return (
    <div
      className="animate-slide-up my-2 flex gap-2.5 rounded-xl px-4 py-3"
      style={{
        background: `linear-gradient(90deg, rgba(239, 68, 68, 0.1), rgba(220, 38, 38, 0.1))`,
        border: `2px solid rgb(239, 68, 68)`,
        boxShadow: `0 0 15px rgba(239, 68, 68, 0.15)`,
      }}
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "rgb(239, 68, 68)" }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span
            className="rounded-full px-2 py-0.5 text-xs font-bold"
            style={{
              background: "rgb(239, 68, 68)",
              color: "white",
            }}
          >
            ERROR
          </span>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: "var(--fr-text-primary)" }}>
          {event.content}
        </p>
      </div>
    </div>
  )
}

function StepEndEvent({ event }: { event: ChatEvent }) {
  return (
    <div
      className="animate-slide-up my-1.5 flex gap-2.5 rounded-lg px-3 py-2.5"
      style={{
        background: `linear-gradient(90deg, rgba(6, 182, 212, 0.06), rgba(59, 130, 246, 0.06))`,
        borderLeft: "3px solid rgb(6, 182, 212)",
      }}
    >
      <Zap className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "rgb(6, 182, 212)" }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold" style={{ color: "rgb(6, 182, 212)" }}>
            STEP COMPLETE
          </span>
        </div>
        {event.content && event.content.trim() && (
          <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--fr-text-secondary)" }}>
            {event.content}
          </p>
        )}
      </div>
    </div>
  )
}

function TextEvent({ event }: { event: ChatEvent }) {
  return (
    <div className="animate-slide-up my-1">
      <p className="text-sm leading-relaxed" style={{ color: "var(--fr-text-primary)" }}>
        {event.content}
      </p>
    </div>
  )
}

export function ChatEventRenderer({ event }: { event: ChatEvent }) {
  // Check for user intervention metadata (think events with user_intervention flag)
  if (event.type === "think" && event.metadata?.user_intervention) {
    return <InterventionEvent event={event} />
  }

  switch (event.type) {
    case "think":
      return <ThinkEvent event={event} />
    case "tool_call":
      return <ToolCallEvent event={event} />
    case "tool_result":
      return <ToolResultEvent event={event} />
    case "ask_user":
      return <AskUserEvent event={event} />
    case "error":
      return <ErrorEvent event={event} />
    case "step_end":
      return <StepEndEvent event={event} />
    case "text":
      return <TextEvent event={event} />
    default:
      return null
  }
}
