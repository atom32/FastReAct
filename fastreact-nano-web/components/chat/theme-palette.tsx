"use client"

import { useTheme, themes, type ThemeName } from "@/lib/theme-context"
import { X } from "lucide-react"

interface ThemePaletteProps {
  isOpen: boolean
  onClose: () => void
}

export function ThemePalette({ isOpen, onClose }: ThemePaletteProps) {
  const { theme, setTheme } = useTheme()

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 animate-fade-in"
        style={{ background: "rgba(0,0,0,0.4)" }}
        onClick={onClose}
      />

      {/* Palette */}
      <div
        className="fixed right-4 top-16 z-50 w-72 animate-modal-in"
        style={{
          background: "var(--fr-bg-secondary)",
          border: `2px solid var(--fr-border-glow)`,
          borderRadius: "20px",
          boxShadow: `0 10px 40px rgba(0,0,0,0.5), 0 0 30px var(--fr-border-glow)`,
          backdropFilter: "blur(20px)",
        }}
      >
        <div className="flex items-center justify-between px-5 pt-4 pb-2">
          <span
            className="text-sm font-semibold"
            style={{ color: "var(--fr-text-primary)" }}
          >
            Choose Theme
          </span>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-lg transition-colors hover:opacity-80"
            style={{ color: "var(--fr-text-muted)" }}
            aria-label="Close palette"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid grid-cols-3 gap-3 p-5">
          {themes.map((t) => {
            const isActive = theme === t.name
            return (
              <button
                key={t.name}
                onClick={() => {
                  setTheme(t.name as ThemeName)
                  onClose()
                }}
                className="group flex flex-col items-center gap-2 transition-transform duration-200 hover:scale-105"
                aria-label={`Switch to ${t.label} theme`}
              >
                <div
                  className="h-14 w-14 rounded-xl transition-all duration-300"
                  style={{
                    background: `linear-gradient(135deg, ${t.swatchColors[0]}, ${t.swatchColors[1]})`,
                    border: isActive
                      ? "3px solid white"
                      : "3px solid transparent",
                    boxShadow: isActive
                      ? `0 0 20px ${t.swatchColors[0]}80`
                      : "none",
                  }}
                />
                <span
                  className="text-[10px] font-medium"
                  style={{
                    color: isActive
                      ? "var(--fr-accent-primary)"
                      : "var(--fr-text-muted)",
                  }}
                >
                  {t.label}
                </span>
              </button>
            )
          })}
        </div>
      </div>
    </>
  )
}
