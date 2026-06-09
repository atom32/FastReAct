"use client"

import { useEffect, useState } from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Trash2, Search, Eye } from "lucide-react"

interface Session {
  session_id: string
  created_at: string
  last_active?: string
  last_activity?: string
  status: string
  user_key?: string
}

interface SessionDetail extends Session {
  events?: Array<{
    type: string
    content?: string
    tool_name?: string
    created_at?: string
    timestamp?: number
  }>
  traces?: Array<{ time_to_first_event_ms?: number; time_to_final_ms?: number; event_count?: number }>
  audit?: Array<{ tool_name: string; decision_level: string }>
  tasks?: Array<{ task_id: string; title: string; status: string }>
}

export function SessionManager() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [selected, setSelected] = useState<SessionDetail | null>(null)

  useEffect(() => {
    fetchSessions()
    const interval = setInterval(fetchSessions, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const fetchSessions = async () => {
    try {
      const response = await fetch("http://localhost:9000/api/sessions")
      if (response.ok) {
        const data = await response.json()
        setSessions(data.sessions || [])
      }
    } catch (error) {
      console.error("Failed to fetch sessions:", error)
    } finally {
      setLoading(false)
    }
  }

  const terminateSession = async (sessionId: string) => {
    if (!confirm("Are you sure you want to terminate this session?")) return

    try {
      const response = await fetch(`http://localhost:9000/api/sessions/${sessionId}`, {
        method: "DELETE",
      })
      if (response.ok) {
        setSessions(sessions.filter((s) => s.session_id !== sessionId))
      }
    } catch (error) {
      console.error("Failed to terminate session:", error)
    }
  }

  const viewSession = async (sessionId: string) => {
    const response = await fetch(`http://localhost:9000/api/sessions/${sessionId}`)
    if (response.ok) {
      setSelected(await response.json())
    }
  }

  const resumeSession = async (sessionId: string) => {
    await fetch(`http://localhost:9000/api/sessions/${sessionId}/resume`, { method: "POST" })
    await viewSession(sessionId)
  }

  const filteredSessions = sessions.filter(
    (s) =>
      searchQuery === "" ||
      s.session_id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button onClick={fetchSessions} variant="outline">
          Refresh
        </Button>
      </div>

      {/* Sessions Table */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Session ID</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Last Active</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  Loading sessions...
                </TableCell>
              </TableRow>
            ) : filteredSessions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  {searchQuery ? "No sessions match your search" : "No active sessions"}
                </TableCell>
              </TableRow>
            ) : (
              filteredSessions.map((session) => (
                <TableRow key={session.session_id}>
                  <TableCell className="font-mono text-sm">
                    {session.session_id.slice(0, 8)}...
                  </TableCell>
                  <TableCell>{formatDate(session.created_at)}</TableCell>
                  <TableCell>{formatDate(session.last_active || session.last_activity || session.created_at)}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{session.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => viewSession(session.session_id)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => terminateSession(session.session_id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Summary */}
      <div className="text-sm text-muted-foreground">
        Showing {filteredSessions.length} of {sessions.length} sessions
      </div>

      {selected && (
        <div className="rounded-lg border p-4">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="font-semibold">Session Detail</div>
              <div className="font-mono text-xs text-muted-foreground">{selected.session_id}</div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => resumeSession(selected.session_id)}>Resume</Button>
              <Button variant="outline" size="sm" onClick={() => setSelected(null)}>Close</Button>
            </div>
          </div>
          <div className="mb-3 grid gap-2 text-sm md:grid-cols-4">
            <div>Status: <Badge variant="outline">{selected.status}</Badge></div>
            <div>User: {selected.user_key || "-"}</div>
            <div>Events: {selected.events?.length || 0}</div>
            <div>Tasks: {selected.tasks?.length || 0}</div>
          </div>
          <div className="mb-3 grid gap-3 md:grid-cols-3">
            <div className="rounded-md border p-3 text-sm">
              <div className="font-medium">Latest Trace</div>
              <div className="text-muted-foreground">
                {selected.traces?.length
                  ? `${selected.traces[selected.traces.length - 1].time_to_first_event_ms ?? "-"}ms first / ${selected.traces[selected.traces.length - 1].time_to_final_ms ?? "-"}ms final`
                  : "No traces"}
              </div>
            </div>
            <div className="rounded-md border p-3 text-sm">
              <div className="font-medium">Audit Records</div>
              <div className="text-muted-foreground">{selected.audit?.length || 0}</div>
            </div>
            <div className="rounded-md border p-3 text-sm">
              <div className="font-medium">Linked Tasks</div>
              <div className="text-muted-foreground">{(selected.tasks || []).map((task) => task.title).join(", ") || "None"}</div>
            </div>
          </div>
          <div className="max-h-80 space-y-2 overflow-y-auto rounded-md bg-muted/30 p-3">
            {(selected.events || []).slice(-50).map((event, index) => (
              <div key={`${event.type}-${index}`} className="rounded border bg-background p-2 text-sm">
                <div className="font-mono text-xs text-muted-foreground">{event.type}{event.tool_name ? `:${event.tool_name}` : ""}</div>
                <div className="max-h-16 overflow-hidden whitespace-pre-wrap">{event.content || "-"}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
