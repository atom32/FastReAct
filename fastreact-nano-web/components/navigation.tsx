"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Settings, ShoppingBag, Rocket, Palette } from "lucide-react"
import { useState, useEffect } from "react"
import type { ConnectionStatus } from "@/lib/chat-types"

interface NavigationProps {
  chatStatus?: ConnectionStatus
  onToggleThemePalette?: () => void
}

export function Navigation({ chatStatus, onToggleThemePalette }: NavigationProps) {
  const pathname = usePathname()
  const isChatPage = pathname === "/"

  return (
    <nav
      className="border-b backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50 glass-panel flex items-center justify-between px-4 py-3 sm:px-6"
      style={{
        borderColor: "var(--fr-border-glow)",
      }}
    >
      <div className="container mx-auto flex w-full items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <Link href="/" className="flex items-center space-x-2">
              <div
                className="h-8 w-8 rounded-lg flex items-center justify-center"
                style={{
                  background: "linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))",
                }}
              >
                <span className="text-white font-bold text-sm">FR</span>
              </div>
              <span
                className="font-bold text-lg hidden sm:inline-block"
                style={{ color: "var(--fr-text-primary)" }}
              >
                FastReAct Nano
              </span>
            </Link>
            <span
              className="text-xs hidden sm:inline-block px-2 py-0.5 rounded-full"
              style={{
                color: "var(--fr-accent-primary)",
                backgroundColor: "rgba(139, 92, 246, 0.1)",
                borderWidth: "1px",
                borderStyle: "solid",
                borderColor: "var(--fr-border-glow)",
              }}
            >
              v2.4.1
            </span>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-1">
            {isChatPage ? (
              // Chat page: Show connection status, theme button, and links
              <>
                {/* Connection Status */}
                {chatStatus && (
                  <div
                    className="hidden items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium sm:flex"
                    style={{
                      color: getStatusColor(chatStatus),
                      backgroundColor: `${getStatusColor(chatStatus)}15`,
                    }}
                  >
                    <span
                      className="block h-2 w-2 rounded-full animate-dot-pulse"
                      style={{ backgroundColor: getStatusColor(chatStatus) }}
                    />
                    {getStatusLabel(chatStatus)}
                  </div>
                )}

                {/* Theme Palette Button */}
                {onToggleThemePalette && (
                  <button
                    onClick={onToggleThemePalette}
                    className="relative flex h-10 w-10 items-center justify-center rounded-full transition-all hover:scale-105 active:scale-95"
                    style={{
                      background: "linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))",
                      boxShadow: "0 4px 12px rgba(139, 92, 246, 0.3)",
                    }}
                  >
                    <Palette className="h-4 w-4 text-white" />
                  </button>
                )}

                <Link
                  href="/admin"
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 hover:opacity-80",
                    "text-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                  style={{ color: "var(--fr-text-secondary)" }}
                >
                  <Settings className="h-4 w-4" />
                  <span className="hidden sm:inline">Admin</span>
                </Link>
                <Link
                  href="/marketplace"
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 hover:opacity-80",
                    "text-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                  style={{ color: "var(--fr-text-secondary)" }}
                >
                  <ShoppingBag className="h-4 w-4" />
                  <span className="hidden sm:inline">Marketplace</span>
                </Link>
              </>
            ) : (
              // Other pages: Show navigation with active state
              <>
                <Link
                  href="/"
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200",
                    pathname === "/" ? "" : "hover:opacity-80"
                  )}
                  style={
                    pathname === "/"
                      ? {
                          background: "linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))",
                          color: "white",
                        }
                      : {
                          color: "var(--fr-text-secondary)",
                        }
                  }
                >
                  <span className="hidden sm:inline">Chat</span>
                </Link>
                <Link
                  href="/admin"
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200",
                    pathname === "/admin" ? "" : "hover:opacity-80"
                  )}
                  style={
                    pathname === "/admin"
                      ? {
                          background: "linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))",
                          color: "white",
                        }
                      : {
                          color: "var(--fr-text-secondary)",
                        }
                  }
                >
                  <Settings className="h-4 w-4" />
                  <span className="hidden sm:inline">Admin</span>
                </Link>
                <Link
                  href="/marketplace"
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200",
                    pathname === "/marketplace" ? "" : "hover:opacity-80"
                  )}
                  style={
                    pathname === "/marketplace"
                      ? {
                          background: "linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))",
                          color: "white",
                        }
                      : {
                          color: "var(--fr-text-secondary)",
                        }
                  }
                >
                  <ShoppingBag className="h-4 w-4" />
                  <span className="hidden sm:inline">Marketplace</span>
                </Link>
              </>
            )}
          </div>
        </div>
    </nav>
  )
}

// Helper functions for connection status
function getStatusColor(status: ConnectionStatus): string {
  switch (status) {
    case "connected":
      return "rgb(34, 197, 94)" // green-500
    case "connecting":
      return "rgb(234, 179, 8)" // yellow-500
    case "disconnected":
      return "rgb(239, 68, 68)" // red-500
    case "error":
      return "rgb(239, 68, 68)" // red-500
    default:
      return "rgb(107, 114, 128)" // gray-500
  }
}

function getStatusLabel(status: ConnectionStatus): string {
  switch (status) {
    case "connected":
      return "Connected"
    case "connecting":
      return "Connecting..."
    case "disconnected":
      return "Disconnected"
    case "error":
      return "Connection Error"
    default:
      return "Unknown"
  }
}
