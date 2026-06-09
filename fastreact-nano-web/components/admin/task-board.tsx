"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { RefreshCw, Plus } from "lucide-react"

interface Task {
  task_id: string
  title: string
  status: string
  priority: string
  owner?: string
  session_id?: string
  updated_at?: string
}

export function TaskBoard() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [title, setTitle] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    setError("")
    try {
      const params = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : ""
      const res = await fetch(`http://localhost:9000/api/tasks${params}`)
      if (res.ok) {
        const data = await res.json()
        setTasks(data.tasks || [])
      } else {
        setError("Failed to load tasks")
      }
    } catch {
      setError("Gateway is unavailable")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [statusFilter])

  const create = async () => {
    if (!title.trim()) return
    setError("")
    const res = await fetch("http://localhost:9000/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, priority: "normal" }),
    })
    if (!res.ok) {
      setError("Failed to create task")
      return
    }
    setTitle("")
    load()
  }

  const setStatus = async (taskId: string, status: string) => {
    const res = await fetch(`http://localhost:9000/api/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    })
    if (!res.ok) {
      setError("Failed to update task")
      return
    }
    load()
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Tasks</CardTitle>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-2 md:flex-row">
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="New task title" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-10 rounded-md border bg-background px-3 text-sm"
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In progress</option>
            <option value="blocked">Blocked</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <Button onClick={create}>
            <Plus className="mr-2 h-4 w-4" />
            Create
          </Button>
        </div>
        {error && <div className="rounded-md border border-destructive/50 px-3 py-2 text-sm text-destructive">{error}</div>}
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Task</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.task_id}>
                  <TableCell>
                    <div className="font-medium">{task.title}</div>
                    <div className="font-mono text-xs text-muted-foreground">{task.task_id}</div>
                  </TableCell>
                  <TableCell><Badge variant="outline">{task.status}</Badge></TableCell>
                  <TableCell>{task.priority}</TableCell>
                  <TableCell>{task.owner || "-"}</TableCell>
                  <TableCell className="space-x-2 text-right">
                    <Button size="sm" variant="outline" onClick={() => setStatus(task.task_id, "in_progress")}>Start</Button>
                    <Button size="sm" variant="outline" onClick={() => setStatus(task.task_id, "completed")}>Done</Button>
                  </TableCell>
                </TableRow>
              ))}
              {!tasks.length && (
                <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground">No tasks</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
