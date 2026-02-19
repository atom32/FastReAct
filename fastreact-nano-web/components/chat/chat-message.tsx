"use client"

import { memo } from "react"
import { User, Bot } from "lucide-react"
import type { ChatMessage } from "@/lib/chat-types"
import { ChatEventRenderer } from "./chat-events"

interface ChatMessageBubbleProps {
  message: ChatMessage
}

export const ChatMessageBubble = memo(function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  if (message.role === "user") {
    return <UserMessage message={message} />
  }
  return <AssistantMessage message={message} />
})

function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="animate-slide-up flex justify-end px-4 sm:px-0">
      <div className="flex max-w-[75%] items-end gap-2 sm:max-w-[65%]">
        <div
          className="rounded-[18px] rounded-br-[4px] px-4 py-3"
          style={{
            background: `linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))`,
            boxShadow: `0 4px 20px var(--fr-border-glow)`,
          }}
        >
          <p className="text-sm leading-relaxed text-white">{message.content}</p>
        </div>
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
          style={{
            background: `linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))`,
          }}
        >
          <User className="h-4 w-4 text-white" />
        </div>
      </div>
    </div>
  )
}

function AssistantMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="animate-slide-up flex justify-start px-4 sm:px-0">
      <div className="flex max-w-[85%] items-start gap-2 sm:max-w-[80%]">
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
          style={{
            background: "var(--fr-bg-tertiary)",
            border: `1px solid var(--fr-border-glow)`,
            boxShadow: `0 0 12px var(--fr-border-glow)`,
          }}
        >
          <Bot className="h-4 w-4" style={{ color: "var(--fr-accent-primary)" }} />
        </div>
        <div
          className="glass-panel min-w-0 flex-1 rounded-[18px] rounded-tl-[4px] p-4"
          style={{
            borderColor: "var(--fr-border-glow)",
            boxShadow: `0 4px 20px rgba(0,0,0,0.2), inset 0 0 0 1px var(--fr-border-glow)`,
          }}
        >
          {/* SKILL Badges */}
          {message.skills && message.skills.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-1">
              {message.skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full px-2 py-0.5 text-xs font-medium"
                  style={{
                    background: "var(--fr-accent-primary)",
                    color: "white",
                  }}
                >
                  {skill}
                </span>
              ))}
            </div>
          )}

          {/* Text content */}
          {message.content && (
            <p className="text-sm leading-relaxed" style={{ color: "var(--fr-text-primary)" }}>
              {message.content}
            </p>
          )}

          {/* Events */}
          {message.events && message.events.length > 0 && (
            <div className="mt-2 flex flex-col gap-1">
              {message.events.map((event) => (
                <ChatEventRenderer key={event.id} event={event} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
