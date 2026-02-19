"use client"

import { Rocket, Settings, Palette } from "lucide-react"
import type { ConnectionStatus } from "@/lib/chat-types"

interface ChatHeaderProps {
  status: ConnectionStatus
  onToggleThemePalette: () => void
  compact?: boolean  // If true, hide logo (used when integrated with global navigation)
}

export function ChatHeader({ status, onToggleThemePalette, compact = false }: ChatHeaderProps) {
  const statusConfig = {
    connected: {
      color: "var(--fr-success)",
      label: "Connected",
    },
    connecting: {
      color: "var(--fr-warning)",
      label: "Reconnecting...",
    },
    disconnected: {
      color: "var(--fr-error)",
      label: "Disconnected",
    },
  }

  const s = statusConfig[status]

  return (
    <header
      className="glass-panel flex items-center justify-between px-4 py-3 sm:px-6"
      style={{
        borderBottom: `1px solid var(--fr-border-glow)`,
      }}
    >
      {/* Left side - Logo (only show if not compact) */}
      {!compact && (
        <div className="flex items-center gap-3">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-xl"
            style={{
              background: `linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))`,
              boxShadow: `0 0 20px var(--fr-border-glow)`,
            }}
          >
            <Rocket className="h-5 w-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span
              className="font-display text-sm font-bold tracking-wider sm:text-base"
              style={{
                background: `linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              FastReAct
            </span>
            <span
              className="text-[10px] font-medium tracking-widest uppercase"
              style={{ color: "var(--fr-text-muted)" }}
            >
              Nano
            </span>
          </div>
        </div>
      )}

      {/* Spacer */}
      {compact && <div className="flex-1" />}

      {/* Right controls */}
      <div className="flex items-center gap-3">
        {/* Status */}
        <div
          className="hidden items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium sm:flex"
          style={{
            background: `${s.color}15`,
            border: `1px solid ${s.color}30`,
            color: s.color,
          }}
        >
          <span
            className="block h-2 w-2 rounded-full animate-dot-pulse"
            style={{ background: s.color }}
          />
          {s.label}
        </div>

        {/* Theme button */}
        <button
          onClick={onToggleThemePalette}
          className="relative flex h-10 w-10 items-center justify-center rounded-full transition-transform duration-200 hover:scale-110"
          style={{
            background: `linear-gradient(135deg, #8b5cf6, #06b6d4, #f472b6, #f59e0b)`,
            border: "2px solid rgba(255,255,255,0.15)",
            boxShadow: `0 4px 16px var(--fr-border-glow)`,
          }}
          aria-label="Toggle theme palette"
        >
          <Palette className="h-4 w-4 text-white" />
        </button>

        {/* Settings */}
        <button
          className="flex h-10 w-10 items-center justify-center rounded-full transition-all duration-200 hover:scale-110"
          style={{
            background: "var(--fr-bg-glass)",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "var(--fr-text-secondary)",
          }}
          aria-label="Settings"
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
