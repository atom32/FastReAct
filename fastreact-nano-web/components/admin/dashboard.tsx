"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, Users, Zap, Clock } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { adminFetch } from "@/lib/gateway"

interface Metrics {
  activeSessions: number
  totalEvents: number
  uptime: number
  memoryUsage: number
  cpuUsage: number
  version?: string
}

interface DependencyHealth {
  status: string
  checks: {
    llm?: { status: string; model?: string }
    store?: { status: string; root?: string; streams?: number; records?: number; bytes?: number }
    mcp?: { status: string; configured_servers?: number }
    gateway?: { status: string; admin_api_auth?: boolean; multitenant?: boolean }
  }
}

export function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics>({
    activeSessions: 0,
    totalEvents: 0,
    uptime: 0,
    memoryUsage: 0,
    cpuUsage: 0,
    version: "2.4.2",
  })
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<DependencyHealth | null>(null)

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const [metricsRes, statusRes, healthRes] = await Promise.all([
          adminFetch("/api/metrics"),
          adminFetch("/api/status"),
          adminFetch("/api/health/dependencies")
        ])

        if (metricsRes.ok) {
          const data = await metricsRes.json()
          // Convert snake_case to camelCase
          setMetrics(prev => ({
            ...prev,
            activeSessions: data.active_sessions,
            totalEvents: data.total_events,
            uptime: data.uptime,
            memoryUsage: data.memory_usage,
            cpuUsage: data.cpu_usage,
          }))
        }

        if (statusRes.ok) {
          const status = await statusRes.json()
          setMetrics(prev => ({ ...prev, version: status.version }))
        }

        if (healthRes.ok) {
          setHealth(await healthRes.json())
        }
      } catch (error) {
        console.error("Failed to fetch metrics:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, 5000) // Refresh every 5s

    return () => clearInterval(interval)
  }, [])

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  const formatMemory = (bytes: number) => {
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(1)} MB`
  }

  const statusBadge = (status?: string) => {
    const healthy = status === "healthy" || status === "configured" || status === "writable"
    const neutral = status === "not_configured" || status === "external"
    return (
      <Badge
        variant="outline"
        className={
          healthy
            ? "border-green-200 bg-green-50 text-green-700"
            : neutral
              ? "border-slate-200 bg-slate-50 text-slate-700"
              : "border-amber-200 bg-amber-50 text-amber-700"
        }
      >
        {status || "unknown"}
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Sessions</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "..." : metrics.activeSessions}
            </div>
            <p className="text-xs text-muted-foreground">Currently connected</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Events</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "..." : metrics.totalEvents}
            </div>
            <p className="text-xs text-muted-foreground">All time</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Uptime</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "..." : formatUptime(metrics.uptime)}
            </div>
            <p className="text-xs text-muted-foreground">Since start</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "..." : formatMemory(metrics.memoryUsage)}
            </div>
            <p className="text-xs text-muted-foreground">RSS</p>
          </CardContent>
        </Card>
      </div>

      {/* System Health */}
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Gateway Status</span>
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              Healthy
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">API Version</span>
            <span className="text-sm text-muted-foreground">{metrics.version || "Unknown"}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Environment</span>
            <span className="text-sm text-muted-foreground">Development</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dependency Health</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium">LLM Provider</span>
            {statusBadge(health?.checks.llm?.status)}
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium">JSONL Store</span>
            {statusBadge(health?.checks.store?.status)}
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium">MCP</span>
            {statusBadge(health?.checks.mcp?.status)}
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium">Admin Auth</span>
            {statusBadge(health?.checks.gateway?.admin_api_auth ? "enabled" : "disabled")}
          </div>
          <div className="md:col-span-2 rounded-md border px-3 py-2 text-xs text-muted-foreground">
            Store: {health?.checks.store?.records ?? 0} records across {health?.checks.store?.streams ?? 0} streams
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            <p>No recent activity to display</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
