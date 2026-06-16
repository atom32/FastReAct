"use client"

import type React from "react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { Activity, ArrowDownUp, CheckCircle2, ChevronLeft, ChevronRight, ClipboardCheck, FileText, Hammer, ListTodo, Play, RefreshCw, Save, Search, Settings2, ShieldCheck } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import {
  getServiceToken,
  serviceHttpBase,
  serviceJson,
  setServiceHttpBase,
  setServiceToken,
  truncateJson,
} from "@/lib/service-api"
import { AssistantRunPanel } from "@/components/service/assistant-run-panel"

type RunRecord = {
  run_id: string
  session_id?: string
  status: string
  created_at?: string
  completed_at?: string
  duration_ms?: number
  event_count?: number
  error?: string
  last_error?: string
  metadata?: Record<string, unknown>
}

type EventRecord = {
  event_id?: string
  sequence?: number
  type: string
  content?: string
  tool_name?: string
  tool_args?: unknown
  cited_source_ids?: string[]
  approval_request_id?: string
  metadata?: Record<string, unknown>
  timestamp?: string
}

type ApprovalRecord = {
  request_id: string
  status: string
  tool_name?: string
  tool_args?: unknown
  reason?: string
  resolution_reason?: string
  policy_scope?: string
  policy_action?: string
}

type WorkspaceFile = {
  name: string
  path: string
  exists: boolean
  content: string
}

type TaskRecord = {
  task_id: string
  title: string
  description?: string
  status: string
  priority: string
  owner?: string
  session_id?: string
  dependencies?: string[]
  created_at?: string
  updated_at?: string
}

type TaskDetail = {
  task: TaskRecord
  runs?: RunRecord[]
  traces?: RunRecord[]
}

type CitationRecord = {
  source_id: string
  event_type: string
  event_id?: string
  title?: string
  url?: string
  snippet?: string
  metadata?: unknown
}

function statusTone(status?: string): string {
  if (status === "completed" || status === "ready" || status === "approved" || status === "allow") {
    return "border-emerald-300 bg-emerald-50 text-emerald-700"
  }
  if (status === "failed" || status === "cancelled" || status === "denied" || status === "deny") {
    return "border-red-300 bg-red-50 text-red-700"
  }
  if (status === "running" || status === "queued" || status === "pending" || status === "require_approval") {
    return "border-amber-300 bg-amber-50 text-amber-700"
  }
  return "border-slate-300 bg-slate-50 text-slate-700"
}

function StatusBadge({ value }: { value?: string }) {
  return <Badge variant="outline" className={statusTone(value)}>{value || "unknown"}</Badge>
}

function timeLabel(value?: string): string {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function traceLabel(trace: RunRecord): string {
  return trace.run_id || trace.session_id || "legacy-trace"
}

function collectCitations(events: EventRecord[]): CitationRecord[] {
  const citations = new Map<string, CitationRecord>()
  for (const event of events) {
    const metadata = event.metadata || {}
    const explicit = Array.isArray((metadata as any).citations) ? (metadata as any).citations : []
    for (const citation of explicit) {
      if (!citation) continue
      const sourceId = String(citation.source_id || citation.id || citation.url || citation.title || "")
      if (!sourceId) continue
      citations.set(`${event.event_id || event.sequence}:${sourceId}`, {
        source_id: sourceId,
        event_type: event.type,
        event_id: event.event_id,
        title: citation.title,
        url: citation.url,
        snippet: citation.snippet || citation.text || citation.content,
        metadata: citation,
      })
    }
    for (const sourceId of event.cited_source_ids || []) {
      citations.set(`${event.event_id || event.sequence}:${sourceId}`, {
        source_id: sourceId,
        event_type: event.type,
        event_id: event.event_id,
        metadata,
      })
    }
    const evidence = Array.isArray((metadata as any).evidence) ? (metadata as any).evidence : []
    for (const item of evidence) {
      if (!item) continue
      const sourceId = String(item.source_id || item.id || item.url || item.title || "")
      if (!sourceId) continue
      citations.set(`${event.event_id || event.sequence}:evidence:${sourceId}`, {
        source_id: sourceId,
        event_type: event.type,
        event_id: event.event_id,
        title: item.title,
        url: item.url,
        snippet: item.snippet || item.text || item.content,
        metadata: item,
      })
    }
  }
  return [...citations.values()]
}

export function ServiceConsole() {
  const [baseUrl, setBaseUrl] = useState(serviceHttpBase())
  const [token, setToken] = useState(getServiceToken())
  const [error, setError] = useState("")
  const [runs, setRuns] = useState<RunRecord[]>([])
  const [traces, setTraces] = useState<RunRecord[]>([])
  const [events, setEvents] = useState<EventRecord[]>([])
  const [selectedRunId, setSelectedRunId] = useState("")
  const [runDetail, setRunDetail] = useState<RunRecord | null>(null)
  const [traceDetail, setTraceDetail] = useState<any>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [tasks, setTasks] = useState<TaskRecord[]>([])
  const [selectedTaskId, setSelectedTaskId] = useState("")
  const [taskDetail, setTaskDetail] = useState<TaskDetail | null>(null)
  const [taskTitle, setTaskTitle] = useState("")
  const [taskDescription, setTaskDescription] = useState("")
  const [taskOwner, setTaskOwner] = useState("")
  const [taskPriority, setTaskPriority] = useState("normal")
  const [skills, setSkills] = useState<any[]>([])
  const [mcpServers, setMcpServers] = useState<any[]>([])
  const [workspaceFiles, setWorkspaceFiles] = useState<WorkspaceFile[]>([])
  const [agentsMd, setAgentsMd] = useState("")
  const [soulMd, setSoulMd] = useState("")
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([])
  const [approvalSummary, setApprovalSummary] = useState<any>(null)
  const [approvalStatusFilter, setApprovalStatusFilter] = useState("")
  const [approvalSessionFilter, setApprovalSessionFilter] = useState("")
  const [approvalRunFilter, setApprovalRunFilter] = useState("")
  const [approvalTaskFilter, setApprovalTaskFilter] = useState("")
  const [approvalOrder, setApprovalOrder] = useState<"desc" | "asc">("desc")
  const [approvalPage, setApprovalPage] = useState(0)
  const [approvalPageSize, setApprovalPageSize] = useState(10)
  const [approvalTotalCount, setApprovalTotalCount] = useState(0)
  const [approvalHasMore, setApprovalHasMore] = useState(false)
  const [policy, setPolicy] = useState<any>(null)
  const [setup, setSetup] = useState<any>(null)
  const [policyTool, setPolicyTool] = useState("exec")
  const [policyArgs, setPolicyArgs] = useState('{"command":"ls"}')
  const [policyResult, setPolicyResult] = useState<any>(null)
  const [wizardModel, setWizardModel] = useState("deepseek-v4-flash")
  const [wizardApiBase, setWizardApiBase] = useState("https://api.deepseek.com")
  const [wizardToken, setWizardToken] = useState("")
  const [wizardWorkspace, setWizardWorkspace] = useState("~/fastreact-pska-workspace")
  const [wizardIncludePska, setWizardIncludePska] = useState(true)
  const [wizardDraft, setWizardDraft] = useState<any>(null)
  const [hydrated, setHydrated] = useState(false)

  const selectedRun = useMemo(
    () => runs.find((run) => run.run_id === selectedRunId) || traces.find((trace) => trace.run_id === selectedRunId),
    [runs, selectedRunId, traces],
  )
  const selectedTask = useMemo(
    () => taskDetail?.task || tasks.find((task) => task.task_id === selectedTaskId),
    [selectedTaskId, taskDetail, tasks],
  )
  const citations = useMemo(() => collectCitations(events), [events])
  const toolCalls = useMemo(() => events.filter((event) => event.type === "tool_call"), [events])
  const approvalEvents = useMemo(() => events.filter((event) => event.type === "ask_user" || event.approval_request_id), [events])
  const approvalStart = approvalTotalCount === 0 ? 0 : approvalPage * approvalPageSize + 1
  const approvalEnd = Math.min(approvalTotalCount, approvalPage * approvalPageSize + approvals.length)

  const saveSettings = useCallback(() => {
    setServiceHttpBase(baseUrl)
    setServiceToken(token)
  }, [baseUrl, token])

  const loadRuns = useCallback(async () => {
    const [runPayload, tracePayload] = await Promise.all([
      serviceJson<{ runs: RunRecord[] }>("/v1/runs?limit=50"),
      serviceJson<{ traces: RunRecord[] }>("/v1/traces?limit=50"),
    ])
    setRuns(runPayload.runs || [])
    setTraces(tracePayload.traces || [])
  }, [])

  const loadEvents = useCallback(async (runId: string) => {
    if (!runId) return
    const payload = await serviceJson<{ events: EventRecord[] }>(`/v1/runs/${runId}/events?limit=500`)
    setEvents(payload.events || [])
  }, [])

  const loadRunDetail = useCallback(async (runId: string) => {
    if (!runId) return
    const run = await serviceJson<RunRecord>(`/v1/runs/${runId}`)
    setRunDetail(run)
    try {
      const trace = await serviceJson<any>(`/v1/traces/${runId}`)
      setTraceDetail(trace.trace || trace)
    } catch {
      setTraceDetail(null)
    }
  }, [])

  const loadTasks = useCallback(async () => {
    const payload = await serviceJson<{ tasks: TaskRecord[] }>("/v1/tasks?limit=100")
    setTasks(payload.tasks || [])
  }, [])

  const loadApprovals = useCallback(async () => {
    const params = new URLSearchParams()
    params.set("limit", String(approvalPageSize))
    params.set("offset", String(approvalPage * approvalPageSize))
    params.set("order", approvalOrder)
    if (approvalStatusFilter) params.set("status", approvalStatusFilter)
    if (approvalSessionFilter) params.set("session_id", approvalSessionFilter)
    if (approvalRunFilter) params.set("run_id", approvalRunFilter)
    if (approvalTaskFilter) params.set("task_id", approvalTaskFilter)
    const payload = await serviceJson<any>(`/v1/approvals?${params.toString()}`)
    setApprovals(payload.approvals || [])
    setApprovalSummary(payload.summary || null)
    setApprovalTotalCount(payload.total_count ?? 0)
    setApprovalHasMore(Boolean(payload.has_more))
  }, [approvalOrder, approvalPage, approvalPageSize, approvalRunFilter, approvalSessionFilter, approvalStatusFilter, approvalTaskFilter])

  const loadTaskDetail = useCallback(async (taskId: string) => {
    if (!taskId) return
    const payload = await serviceJson<TaskDetail>(`/v1/tasks/${taskId}`)
    setTaskDetail(payload)
  }, [])

  const refreshAll = useCallback(async () => {
    setError("")
    try {
      const [setupPayload, skillsPayload, policyPayload] = await Promise.all([
        serviceJson<any>("/v1/setup"),
        serviceJson<any>("/v1/skills/diagnostics"),
        serviceJson<any>("/v1/policy"),
      ])
      setSetup(setupPayload)
      setSkills(skillsPayload.skills || [])
      setMcpServers(skillsPayload.mcp_servers || [])
      setPolicy(policyPayload)
      await Promise.all([loadRuns(), loadTasks(), loadApprovals()])
      if (selectedRunId) await loadEvents(selectedRunId)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }, [loadApprovals, loadEvents, loadRuns, loadTasks, selectedRunId])

  const loadWorkspace = useCallback(async () => {
    const payload = await serviceJson<{ files: WorkspaceFile[] }>("/v1/workspace/profile")
    setWorkspaceFiles(payload.files || [])
    setAgentsMd((payload.files || []).find((file) => file.name === "AGENTS.md")?.content || "")
    setSoulMd((payload.files || []).find((file) => file.name === "SOUL.md")?.content || "")
  }, [])

  useEffect(() => {
    setHydrated(true)
    refreshAll()
    loadWorkspace().catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [loadWorkspace, refreshAll])

  useEffect(() => {
    if (!selectedRunId && runs[0]?.run_id) {
      setSelectedRunId(runs[0].run_id)
    }
  }, [runs, selectedRunId])

  useEffect(() => {
    if (!selectedTaskId && tasks[0]?.task_id) {
      setSelectedTaskId(tasks[0].task_id)
    }
  }, [selectedTaskId, tasks])

  useEffect(() => {
    setApprovalPage(0)
  }, [approvalOrder, approvalPageSize, approvalRunFilter, approvalSessionFilter, approvalStatusFilter, approvalTaskFilter])

  useEffect(() => {
    if (!hydrated) return
    loadApprovals().catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [hydrated, loadApprovals])

  useEffect(() => {
    if (selectedRunId) {
      Promise.all([loadEvents(selectedRunId), loadRunDetail(selectedRunId)]).catch((err) => setError(err instanceof Error ? err.message : String(err)))
    }
  }, [loadEvents, loadRunDetail, selectedRunId])

  useEffect(() => {
    if (selectedTaskId) {
      loadTaskDetail(selectedTaskId).catch((err) => setError(err instanceof Error ? err.message : String(err)))
    }
  }, [loadTaskDetail, selectedTaskId])

  useEffect(() => {
    loadApprovals().catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [loadApprovals])

  async function startTaskRun(task: TaskRecord) {
    const taskQuery = task.description?.trim()
      ? `${task.title}\n\n${task.description}`
      : task.title
    saveSettings()
    setError("")
    setIsRunning(true)
    try {
      const payload = await serviceJson<RunRecord & { run_id: string }>("/v1/runs", {
        method: "POST",
        body: JSON.stringify({
          messages: [{ role: "user", content: taskQuery }],
          stream: true,
          session_id: task.session_id || undefined,
          metadata: { source: "service_console", task_id: task.task_id },
        }),
      })
      setSelectedRunId(payload.run_id)
      await serviceJson(`/v1/tasks/${task.task_id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "in_progress", session_id: payload.session_id }),
      })
      await Promise.all([loadRuns(), loadTasks(), loadEvents(payload.run_id)])
      const timer = window.setInterval(async () => {
        await Promise.all([loadRuns(), loadEvents(payload.run_id)])
        const latest = await serviceJson<RunRecord>(`/v1/runs/${payload.run_id}`)
        if (["completed", "failed", "cancelled", "expired"].includes(latest.status)) {
          window.clearInterval(timer)
          setIsRunning(false)
          await loadTasks()
        }
      }, 1200)
    } catch (err) {
      setIsRunning(false)
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function createTask() {
    if (!taskTitle.trim()) return
    setError("")
    try {
      const payload = await serviceJson<{ task: TaskRecord }>("/v1/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: taskTitle,
          description: taskDescription,
          owner: taskOwner,
          priority: taskPriority,
        }),
      })
      setTaskTitle("")
      setTaskDescription("")
      setSelectedTaskId(payload.task.task_id)
      await loadTasks()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function updateTaskStatus(taskId: string, status: string) {
    await serviceJson(`/v1/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    })
    await loadTasks()
  }

  async function cancelRun(runId: string) {
    await serviceJson(`/v1/runs/${runId}/cancel`, { method: "POST" })
    await loadRuns()
    await loadEvents(runId)
  }

  async function saveWorkspace() {
    setError("")
    try {
      await serviceJson("/v1/workspace/profile", {
        method: "PUT",
        body: JSON.stringify({ agents_md: agentsMd, soul_md: soulMd }),
      })
      await loadWorkspace()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function resolveApproval(requestId: string, approved: boolean) {
    await serviceJson(`/v1/approvals/${requestId}/${approved ? "approve" : "deny"}`, {
      method: "POST",
      body: JSON.stringify({ reason: "Resolved from FastReAct service console" }),
    })
    await refreshAll()
  }

  async function checkPolicy() {
    let args: Record<string, unknown> = {}
    try {
      args = JSON.parse(policyArgs || "{}")
    } catch {
      setError("Policy args must be valid JSON.")
      return
    }
    const result = await serviceJson("/v1/policy/check", {
      method: "POST",
      body: JSON.stringify({ tool_name: policyTool, tool_args: args }),
    })
    setPolicyResult(result)
  }

  async function generateConfigDraft() {
    setError("")
    try {
      const draft = await serviceJson<any>("/v1/setup/config-draft", {
        method: "POST",
        body: JSON.stringify({
          preset: wizardIncludePska ? "pska" : "default",
          include_pska: wizardIncludePska,
          model: wizardModel,
          api_base: wizardApiBase || null,
          service_token: wizardToken || null,
          workspace: wizardWorkspace,
        }),
      })
      setWizardDraft(draft)
      if (!wizardToken && draft.service_token) {
        setWizardToken(draft.service_token)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <main className={`service-console${hydrated ? " service-console--hydrated" : ""} container mx-auto max-w-7xl px-4 py-6 relative z-10`}>
      <div className="service-console__topbar mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold" style={{ color: "var(--fr-text-primary)" }}>Daemon Console</h1>
          <p className="mt-1 text-sm" style={{ color: "var(--fr-text-secondary)" }}>
            Single-agent service shell for runs, traces, skills, workspace profile, approvals, and setup.
          </p>
        </div>
        <div className="service-console__settings grid gap-2 sm:grid-cols-[minmax(220px,320px)_minmax(180px,260px)_auto]">
          <Input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} aria-label="Service URL" />
          <Input value={token} onChange={(event) => setToken(event.target.value)} type="password" aria-label="Service token" placeholder="Service token" />
          <Button onClick={() => { saveSettings(); refreshAll() }}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      <Tabs defaultValue="chat" className="space-y-5">
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1">
          <TabsTrigger value="chat"><Play className="mr-2 h-4 w-4" />Chat/Run</TabsTrigger>
          <TabsTrigger value="runs"><Activity className="mr-2 h-4 w-4" />Runs/Trace</TabsTrigger>
          <TabsTrigger value="tasks"><ListTodo className="mr-2 h-4 w-4" />Tasks</TabsTrigger>
          <TabsTrigger value="skills"><Hammer className="mr-2 h-4 w-4" />Skills</TabsTrigger>
          <TabsTrigger value="workspace"><FileText className="mr-2 h-4 w-4" />Workspace</TabsTrigger>
          <TabsTrigger value="approvals"><ClipboardCheck className="mr-2 h-4 w-4" />Approvals</TabsTrigger>
          <TabsTrigger value="setup"><Settings2 className="mr-2 h-4 w-4" />Setup</TabsTrigger>
        </TabsList>

        <TabsContent forceMount value="chat">
          <AssistantRunPanel
            selectedRunId={selectedRunId}
            selectedRun={runDetail || selectedRun || null}
            events={events}
            isRunning={isRunning}
            onRunCreated={async (run) => {
              setSelectedRunId(run.run_id)
              await loadRuns()
            }}
            onRefreshRun={async (runId) => {
              await Promise.all([loadRuns(), loadEvents(runId), loadRunDetail(runId), loadApprovals()])
            }}
            onCancelRun={cancelRun}
            onResolveApproval={resolveApproval}
            onError={setError}
            onRunningChange={setIsRunning}
            onSaveSettings={saveSettings}
          />
        </TabsContent>

        <TabsContent forceMount value="runs" className="grid gap-4 lg:grid-cols-[380px_minmax(0,1fr)]">
          <Card>
            <CardHeader><CardTitle>Runs</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {runs.map((run, index) => (
                <button
                  key={`${run.run_id}-${index}`}
                  onClick={() => setSelectedRunId(run.run_id)}
                  className="w-full rounded-md border p-3 text-left text-sm hover:bg-muted"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs">{run.run_id.slice(0, 13)}</span>
                    <StatusBadge value={run.status} />
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">{timeLabel(run.created_at)} · {run.event_count ?? 0} events</div>
                </button>
              ))}
            </CardContent>
          </Card>
          <div className="space-y-4">
            {selectedRun && <RunSummary run={runDetail || selectedRun} trace={traceDetail} events={events} />}
            <EventStream events={events} />
            <CitationPanel citations={citations} />
            <Card>
              <CardHeader><CardTitle>Replay Summary</CardTitle></CardHeader>
              <CardContent className="grid gap-2 md:grid-cols-2 text-sm">
                <div className="rounded-md border p-2">Events: {events.length}</div>
                <div className="rounded-md border p-2">Tool calls: {toolCalls.length}</div>
                <div className="rounded-md border p-2">Approvals: {approvalEvents.length}</div>
                <div className="rounded-md border p-2">Citations: {citations.length}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Trace Summaries</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                {traces.map((trace, index) => (
                  <button
                    key={`${traceLabel(trace)}-${index}`}
                    onClick={() => trace.run_id && setSelectedRunId(trace.run_id)}
                    disabled={!trace.run_id}
                    className="w-full rounded-md border p-3 text-left text-sm hover:bg-muted"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs">{traceLabel(trace)}</span>
                      <StatusBadge value={trace.status} />
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {trace.run_id ? "replayable" : "legacy summary"} · {timeLabel(trace.completed_at)} · {trace.duration_ms ?? "-"} ms
                    </div>
                  </button>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent forceMount value="tasks" className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_420px]">
          <Card>
            <CardHeader><CardTitle>Task Board</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {tasks.map((task, index) => (
                <button
                  key={`${task.task_id}-${index}`}
                  onClick={() => setSelectedTaskId(task.task_id)}
                  className="w-full rounded-md border p-3 text-left text-sm hover:bg-muted"
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="font-medium">{task.title}</span>
                    <StatusBadge value={task.status} />
                  </div>
                  <div className="font-mono text-xs text-muted-foreground">{task.task_id}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {task.priority} · {task.owner || "unowned"} · {timeLabel(task.updated_at)}
                  </div>
                </button>
              ))}
              {!tasks.length && <div className="rounded-md border p-3 text-sm text-muted-foreground">No durable tasks yet.</div>}
            </CardContent>
          </Card>
          <div className="space-y-4">
            <Card>
              <CardHeader><CardTitle>Create Task</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <Input value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} placeholder="Task title" />
                <Textarea value={taskDescription} onChange={(event) => setTaskDescription(event.target.value)} className="min-h-[120px]" placeholder="Description or acceptance criteria" />
                <div className="grid gap-2 md:grid-cols-2">
                  <Input value={taskOwner} onChange={(event) => setTaskOwner(event.target.value)} placeholder="Owner or tenant" />
                  <select value={taskPriority} onChange={(event) => setTaskPriority(event.target.value)} className="h-10 rounded-md border bg-background px-3 text-sm">
                    <option value="low">Low</option>
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
                <Button onClick={createTask} disabled={!taskTitle.trim()}><ListTodo className="mr-2 h-4 w-4" />Create Task</Button>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Task Detail</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {selectedTask ? (
                  <>
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-medium">{selectedTask.title}</div>
                      <StatusBadge value={selectedTask.status} />
                    </div>
                    <div className="font-mono text-xs text-muted-foreground">{selectedTask.task_id}</div>
                    {selectedTask.description && <div className="whitespace-pre-wrap text-sm">{selectedTask.description}</div>}
                    <div className="grid gap-2 md:grid-cols-2 text-sm">
                      <div className="rounded-md border p-2">Priority: {selectedTask.priority}</div>
                      <div className="rounded-md border p-2">Owner: {selectedTask.owner || "-"}</div>
                      <div className="rounded-md border p-2">Session: {selectedTask.session_id || "-"}</div>
                      <div className="rounded-md border p-2">Updated: {timeLabel(selectedTask.updated_at)}</div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => updateTaskStatus(selectedTask.task_id, "in_progress")}>Start</Button>
                      <Button size="sm" variant="outline" onClick={() => updateTaskStatus(selectedTask.task_id, "blocked")}>Block</Button>
                      <Button size="sm" variant="outline" onClick={() => updateTaskStatus(selectedTask.task_id, "completed")}>Complete</Button>
                      <Button size="sm" variant="outline" onClick={() => updateTaskStatus(selectedTask.task_id, "cancelled")}>Cancel</Button>
                      <Button size="sm" onClick={() => startTaskRun(selectedTask)} disabled={isRunning}>
                        <Play className="mr-2 h-4 w-4" />Run Task
                      </Button>
                    </div>
                    <div className="rounded-md border p-3 text-sm">
                      Related runs: {taskDetail?.runs?.length ?? 0} · traces: {taskDetail?.traces?.length ?? 0}
                    </div>
                    {(taskDetail?.runs || []).slice(0, 5).map((run, index) => (
                      <button
                        key={`${run.run_id}-${index}`}
                        className="w-full rounded-md border p-2 text-left text-sm hover:bg-muted"
                        onClick={() => setSelectedRunId(run.run_id)}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs">{run.run_id}</span>
                          <StatusBadge value={run.status} />
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">{timeLabel(run.created_at)} · {run.event_count ?? 0} events</div>
                      </button>
                    ))}
                  </>
                ) : (
                  <div className="text-sm text-muted-foreground">Select or create a task.</div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent forceMount value="skills" className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Card>
            <CardHeader><CardTitle>Skills</CardTitle></CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              {skills.map((skill, index) => (
                <div key={`${skill.name}-${index}`} className="rounded-md border p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <div className="font-medium">{skill.name}</div>
                    <StatusBadge value={skill.status} />
                  </div>
                  <p className="text-sm text-muted-foreground">{skill.description}</p>
                  <div className="mt-3 flex flex-wrap gap-1">
                    {(skill.mcp_servers || []).map((name: string, itemIndex: number) => <Badge key={`mcp-${name}-${itemIndex}`} variant="secondary">{name}</Badge>)}
                    {(skill.recommended_tools || []).map((name: string, itemIndex: number) => <Badge key={`tool-${name}-${itemIndex}`} variant="outline">{name}</Badge>)}
                  </div>
                  {(skill.missing_tools?.length || skill.missing_mcp_servers?.length) ? (
                    <pre className="mt-3 rounded bg-muted p-2 text-xs">{truncateJson({ missing_tools: skill.missing_tools, missing_mcp_servers: skill.missing_mcp_servers })}</pre>
                  ) : null}
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>MCP Servers</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {mcpServers.map((server, index) => (
                <div key={`${server.name || "server"}-${index}`} className="rounded-md border p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{server.name || "server"}</span>
                    <StatusBadge value={server.alive ? "ready" : "degraded"} />
                  </div>
                  {server.error && <div className="mt-2 text-xs text-red-700">{server.error}</div>}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent forceMount value="workspace" className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Card>
            <CardHeader><CardTitle>Workspace Profile</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>AGENTS.md</Label>
                  <Textarea value={agentsMd} onChange={(event) => setAgentsMd(event.target.value)} className="min-h-[360px] font-mono text-sm" />
                </div>
                <div className="space-y-2">
                  <Label>SOUL.md</Label>
                  <Textarea value={soulMd} onChange={(event) => setSoulMd(event.target.value)} className="min-h-[360px] font-mono text-sm" />
                </div>
              </div>
              <Button onClick={saveWorkspace}><Save className="mr-2 h-4 w-4" />Save Profile</Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Loaded Files</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {workspaceFiles.map((file, index) => (
                <div key={`${file.path}-${index}`} className="rounded-md border p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{file.name}</span>
                    <StatusBadge value={file.exists ? "loaded" : "missing"} />
                  </div>
                  <div className="mt-1 break-all text-xs text-muted-foreground">{file.path}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent forceMount value="approvals" className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_420px]">
          <Card>
            <CardHeader><CardTitle>Approval Queue</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-md border p-2 text-sm text-muted-foreground">
                Pending approvals pause the matching tool call until an operator approves, denies, or the request expires.
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                <select value={approvalStatusFilter} onChange={(event) => setApprovalStatusFilter(event.target.value)}>
                  <option value="">All statuses</option>
                  <option value="pending">Pending</option>
                  <option value="approved">Approved</option>
                  <option value="denied">Denied</option>
                  <option value="expired">Expired</option>
                </select>
                <Input value={approvalSessionFilter} onChange={(event) => setApprovalSessionFilter(event.target.value)} placeholder="Session filter" />
                <Input value={approvalRunFilter} onChange={(event) => setApprovalRunFilter(event.target.value)} placeholder="Run filter" />
                <Input value={approvalTaskFilter} onChange={(event) => setApprovalTaskFilter(event.target.value)} placeholder="Task filter" />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <div className="text-muted-foreground">
                  Showing {approvalStart}-{approvalEnd} of {approvalTotalCount}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={approvalPageSize}
                    onChange={(event) => setApprovalPageSize(Number(event.target.value))}
                    aria-label="Approval page size"
                    className="w-[92px]"
                  >
                    <option value={10}>10 / page</option>
                    <option value={25}>25 / page</option>
                    <option value={50}>50 / page</option>
                  </select>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setApprovalOrder((value) => (value === "desc" ? "asc" : "desc"))}
                    title={approvalOrder === "desc" ? "Newest first" : "Oldest first"}
                  >
                    <ArrowDownUp className="mr-2 h-4 w-4" />
                    {approvalOrder === "desc" ? "Newest first" : "Oldest first"}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={approvalPage === 0}
                    onClick={() => setApprovalPage((page) => Math.max(0, page - 1))}
                    title="Previous page"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!approvalHasMore}
                    onClick={() => setApprovalPage((page) => page + 1)}
                    title="Next page"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2 text-sm">
                <div className="rounded-md border p-2">Pending: {approvalSummary?.pending_count ?? 0}</div>
                <div className="rounded-md border p-2">Expired: {approvalSummary?.expired_count ?? 0}</div>
                <div className="rounded-md border p-2">Total: {approvalSummary?.count ?? approvalTotalCount}</div>
                <div className="rounded-md border p-2">Avg resolution: {approvalSummary?.avg_resolution_ms ?? "-"} ms</div>
              </div>
              {approvals.map((approval, index) => (
                <div key={`${approval.request_id}-${index}`} className="rounded-md border p-3 text-sm">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="font-mono text-xs">{approval.request_id}</span>
                    <StatusBadge value={approval.status} />
                  </div>
                  <div className="font-medium">{approval.tool_name}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {approval.policy_scope || "no policy scope"} · {approval.policy_action || "no policy action"}
                  </div>
                  <div className="mt-1 text-muted-foreground">{approval.reason || approval.resolution_reason || "-"}</div>
                  <pre className="mt-2 rounded bg-muted p-2 text-xs">{truncateJson(approval.tool_args)}</pre>
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" disabled={approval.status !== "pending"} onClick={() => resolveApproval(approval.request_id, true)}>Approve</Button>
                    <Button size="sm" variant="outline" disabled={approval.status !== "pending"} onClick={() => resolveApproval(approval.request_id, false)}>Deny</Button>
                  </div>
                </div>
              ))}
              {!approvals.length && <div className="rounded-md border p-3 text-sm text-muted-foreground">No approvals match the current filters.</div>}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Policy Check</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-md border p-3 text-sm">
                <div>Policy version</div>
                <div className="mt-1 break-all font-mono text-xs text-muted-foreground">{policy?.policy_version || policy?.policy_snapshot_hash || "-"}</div>
                <div className="mt-2">Runtime reload: {policy?.reload_supported ? "supported" : "restart required"}</div>
              </div>
              <Input value={policyTool} onChange={(event) => setPolicyTool(event.target.value)} />
              <Textarea value={policyArgs} onChange={(event) => setPolicyArgs(event.target.value)} className="min-h-[120px] font-mono text-sm" />
              <Button onClick={checkPolicy}><ShieldCheck className="mr-2 h-4 w-4" />Check</Button>
              {policyResult && <pre className="rounded bg-muted p-3 text-xs">{truncateJson(policyResult, 1600)}</pre>}
              <pre className="rounded bg-muted p-3 text-xs">{truncateJson(policy, 1600)}</pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent forceMount value="setup" className="grid gap-4 lg:grid-cols-3">
          <SetupPanel title="Model" icon={<Search className="h-4 w-4" />} value={setup?.readiness?.model?.name || "not configured"} status={setup?.readiness?.model?.api_key_configured ? "ready" : "missing_key"} body={setup?.readiness?.model} />
          <SetupPanel title="Service" icon={<CheckCircle2 className="h-4 w-4" />} value={`${setup?.service?.host || "-"}:${setup?.service?.port || "-"}`} status={setup?.service?.auth_required ? "auth_required" : "open"} body={setup?.service} />
          <SetupPanel title="PSKA Preset" icon={<ShieldCheck className="h-4 w-4" />} value={setup?.presets?.pska?.config_file || "config.pska.example.json"} status={setup?.presets?.pska?.protocol_only ? "protocol_only" : "unknown"} body={setup?.presets?.pska} />
          <Card className="lg:col-span-3">
            <CardHeader><CardTitle>Configuration Wizard</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Model</Label>
                  <Input value={wizardModel} onChange={(event) => setWizardModel(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>API Base</Label>
                  <Input value={wizardApiBase} onChange={(event) => setWizardApiBase(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Service Token</Label>
                  <Input value={wizardToken} onChange={(event) => setWizardToken(event.target.value)} placeholder="Leave empty to generate" />
                </div>
                <div className="space-y-2">
                  <Label>Workspace</Label>
                  <Input value={wizardWorkspace} onChange={(event) => setWizardWorkspace(event.target.value)} />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={wizardIncludePska}
                  onChange={(event) => setWizardIncludePska(event.target.checked)}
                  className="h-4 w-4"
                />
                Include PSKA MCP preset and tenant-safe policy
              </label>
              <Button onClick={generateConfigDraft}><Settings2 className="mr-2 h-4 w-4" />Generate Draft</Button>
              {wizardDraft && (
                <div className="space-y-2">
                  <div className="rounded-md border p-3 text-sm">
                    Recommended path: {wizardDraft.recommended_path} · writes file: {wizardDraft.write_supported ? "yes" : "no"}
                  </div>
                  <pre className="max-h-[520px] overflow-auto rounded bg-muted p-3 text-xs">{truncateJson(wizardDraft.config, 9000)}</pre>
                </div>
              )}
            </CardContent>
          </Card>
          <Card className="lg:col-span-3">
            <CardHeader><CardTitle>Setup Snapshot</CardTitle></CardHeader>
            <CardContent><pre className="max-h-[420px] overflow-auto rounded bg-muted p-3 text-xs">{truncateJson(setup, 6000)}</pre></CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </main>
  )
}

function EventStream({ events }: { events: EventRecord[] }) {
  return (
    <Card>
      <CardHeader><CardTitle>Event Stream</CardTitle></CardHeader>
      <CardContent className="max-h-[680px] space-y-2 overflow-auto">
        {events.map((event, index) => (
          <div key={event.event_id || `${event.type}-${event.sequence ?? index}-${index}`} className="rounded-md border p-3 text-sm">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{event.sequence ?? "-"}</Badge>
                <span className="font-medium">{event.type}</span>
              </div>
              {event.tool_name && <Badge variant="outline">{event.tool_name}</Badge>}
            </div>
            {event.content && <div className="whitespace-pre-wrap text-sm">{event.content}</div>}
            {event.tool_args ? <pre className="mt-2 rounded bg-muted p-2 text-xs">{truncateJson(event.tool_args)}</pre> : null}
            {event.cited_source_ids?.length ? <div className="mt-2 text-xs text-muted-foreground">Citations: {event.cited_source_ids.join(", ")}</div> : null}
            {event.approval_request_id ? <div className="mt-2 text-xs text-amber-700">Approval: {event.approval_request_id}</div> : null}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function RunSummary({ run, trace, events }: { run: RunRecord; trace: any; events: EventRecord[] }) {
  const error = run.error || run.last_error || trace?.error || trace?.error_summary
  const finalContent = trace?.final_content || trace?.final_answer || events.find((event) => event.type === "session_end")?.content
  const toolCount = trace?.tool_call_count ?? events.filter((event) => event.type === "tool_call").length
  const approvalCount = trace?.approval_count ?? events.filter((event) => event.type === "ask_user" || event.approval_request_id).length
  const compressionCount = trace?.compression_count ?? events.filter((event) => event.metadata?.compression).length
  return (
    <Card>
      <CardHeader><CardTitle>Run Detail</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-xs">{run.run_id}</span>
          <StatusBadge value={run.status} />
        </div>
        <div className="grid gap-2 md:grid-cols-2 text-sm">
          <div className="rounded-md border p-2">Session: {run.session_id || "-"}</div>
          <div className="rounded-md border p-2">Events: {run.event_count ?? events.length}</div>
          <div className="rounded-md border p-2">Tools: {toolCount}</div>
          <div className="rounded-md border p-2">Approvals: {approvalCount}</div>
          <div className="rounded-md border p-2">Compression: {compressionCount}</div>
          <div className="rounded-md border p-2">Duration: {run.duration_ms ?? trace?.duration_ms ?? "-"} ms</div>
        </div>
        {trace?.policy_snapshot_hash && (
          <div className="rounded-md border p-2 text-xs">Policy snapshot: <span className="font-mono">{trace.policy_snapshot_hash}</span></div>
        )}
        {error && <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">{String(error)}</div>}
        {finalContent && (
          <div>
            <div className="mb-1 text-sm font-medium">Final Content</div>
            <div className="max-h-[220px] overflow-auto rounded-md border p-3 text-sm whitespace-pre-wrap">{finalContent}</div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function CitationPanel({ citations }: { citations: CitationRecord[] }) {
  return (
    <Card>
      <CardHeader><CardTitle>Citations</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {citations.map((citation, index) => (
          <div key={`${citation.event_id || citation.event_type}-${citation.source_id}-${index}`} className="rounded-md border p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{citation.title || citation.source_id}</span>
              <Badge variant="outline">{citation.event_type}</Badge>
            </div>
            {citation.url && <div className="mt-1 break-all text-xs text-muted-foreground">{citation.url}</div>}
            {citation.snippet && <div className="mt-2 whitespace-pre-wrap text-sm">{citation.snippet}</div>}
            {!citation.snippet && citation.metadata ? <pre className="mt-2 rounded bg-muted p-2 text-xs">{truncateJson(citation.metadata, 700)}</pre> : null}
          </div>
        ))}
        {!citations.length && <div className="rounded-md border p-3 text-sm text-muted-foreground">No citation or evidence metadata in this replay.</div>}
      </CardContent>
    </Card>
  )
}

function SetupPanel({ title, icon, value, status, body }: { title: string; icon: React.ReactNode; value: string; status: string; body: unknown }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">{icon}{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="break-all text-sm font-medium">{value}</div>
        <StatusBadge value={status} />
        <pre className="max-h-[180px] overflow-auto rounded bg-muted p-2 text-xs">{truncateJson(body)}</pre>
      </CardContent>
    </Card>
  )
}
