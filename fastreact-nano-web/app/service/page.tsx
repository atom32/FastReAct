"use client"

import { Navigation } from "@/components/navigation"
import { ServiceConsole } from "@/components/service/service-console"
import { ThemeProvider } from "@/lib/theme-context"

export default function ServicePage() {
  return (
    <ThemeProvider>
      <div className="min-h-screen" style={{ background: "var(--fr-bg-primary)" }}>
        <div className="background-mesh" />
        <Navigation />
        <ServiceConsole />
      </div>
    </ThemeProvider>
  )
}
