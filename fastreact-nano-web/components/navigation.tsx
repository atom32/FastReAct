"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Settings, ShoppingBag } from "lucide-react"

export function Navigation() {
  const pathname = usePathname()
  const isChatPage = pathname === "/"

  return (
    <nav
      className="border-b backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50"
      style={{
        background: "var(--fr-bg-glass)",
        borderColor: "var(--fr-border-glow)",
      }}
    >
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
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
              // Chat page: Show links to Admin and Marketplace
              <>
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
      </div>
    </nav>
  )
}
