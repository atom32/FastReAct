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

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const [metricsRes, statusRes] = await Promise.all([
          adminFetch("/api/metrics"),
          adminFetch("/api/status")
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
