"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"

export type ThemeName = "cyber-dark" | "midnight" | "solar-light" | "forest" | "sunset" | "matrix"

export interface ThemeConfig {
  name: ThemeName
  label: string
  swatchColors: string[]
  isLight: boolean
}

export const themes: ThemeConfig[] = [
  {
    name: "cyber-dark",
    label: "Cyber Dark",
    swatchColors: ["#8b5cf6", "#06b6d4"],
    isLight: false,
  },
  {
    name: "midnight",
    label: "Midnight",
    swatchColors: ["#3b82f6", "#1e293b"],
    isLight: false,
  },
  {
    name: "solar-light",
    label: "Solar Light",
    swatchColors: ["#f59e0b", "#fffbeb"],
    isLight: true,
  },
  {
    name: "forest",
    label: "Forest",
    swatchColors: ["#10b981", "#052e16"],
    isLight: false,
  },
  {
    name: "sunset",
    label: "Sunset",
    swatchColors: ["#fb923c", "#f472b6"],
    isLight: false,
  },
  {
    name: "matrix",
    label: "Matrix",
    swatchColors: ["#22c55e", "#000000"],
    isLight: false,
  },
]

interface ThemeContextValue {
  theme: ThemeName
  setTheme: (theme: ThemeName) => void
  config: ThemeConfig
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeName>("cyber-dark")

  useEffect(() => {
    const saved = localStorage.getItem("fastreact-theme") as ThemeName | null
    if (saved && themes.some((t) => t.name === saved)) {
      setThemeState(saved)
    }
  }, [])

  const setTheme = (t: ThemeName) => {
    setThemeState(t)
    localStorage.setItem("fastreact-theme", t)
  }

  const config = themes.find((t) => t.name === theme) || themes[0]

  return (
    <ThemeContext.Provider value={{ theme, setTheme, config }}>
      <div
        data-theme={theme}
        className="min-h-screen transition-colors duration-500"
        style={{ background: "var(--fr-bg-primary)", color: "var(--fr-text-primary)" }}
      >
        <div className="background-mesh" />
        {children}
      </div>
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider")
  return ctx
}
