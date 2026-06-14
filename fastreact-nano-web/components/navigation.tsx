"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Rocket } from "lucide-react"

export function Navigation() {
  const pathname = usePathname()

  return (
    <nav
      className="border-b backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50 glass-panel flex items-center justify-between px-4 py-3 sm:px-6"
      style={{ borderColor: "var(--fr-border-glow)" }}
    >
      <div className="container mx-auto flex w-full items-center justify-between">
        <div className="flex items-center gap-2">
          <Link href="/service" className="flex items-center space-x-2">
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
            Daemon 1.0
          </span>
        </div>

        <Link
          href="/service"
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200",
            pathname === "/service" ? "" : "hover:opacity-80"
          )}
          style={
            pathname === "/service"
              ? {
                  background: "linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))",
                  color: "white",
                }
              : {
                  color: "var(--fr-text-secondary)",
                }
          }
        >
          <Rocket className="h-4 w-4" />
          <span className="hidden sm:inline">Service</span>
        </Link>
      </div>
    </nav>
  )
}
