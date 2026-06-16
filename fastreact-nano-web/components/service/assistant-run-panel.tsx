"use client"

import type React from "react"
import { useEffect, useMemo, useRef, useState } from "react"
import {
  AssistantRuntimeProvider,
  ThreadPrimitive,
  type AppendMessage,
  useExternalStoreRuntime,
} from "@assistant-ui/react"
import { AlertTriangle, Bot, Check, Clipboard, Copy, MessageSquare, Play, RefreshCw, ShieldQuestion, Sparkles, StopCircle, Terminal, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { serviceJson, truncateJson } from "@/lib/service-api"
import {
  fastReactEventsToThreadMessages,
  type FastReactApprovalBlock,
  type FastReactCitation,
  type FastReactRunEvent,
  type FastReactThreadMessage,
  type FastReactToolBlock,
} from "@/lib/fastreact-thread"

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

type AssistantRunPanelProps = {
  selectedRunId: string
  selectedRun?: RunRecord | null
  events: FastReactRunEvent[]
  isRunning: boolean
  onRunCreated: (run: RunRecord) => Promise<void> | void
  onRefreshRun: (runId: string) => Promise<void> | void
  onCancelRun: (runId: string) => Promise<void> | void
  onResolveApproval: (requestId: string, approved: boolean) => Promise<void> | void
  onError: (message: string) => void
  onRunningChange: (running: boolean) => void
  onSaveSettings: () => void
}

function statusTone(status?: string): string {
  if (status === "completed" || status === "complete" || status === "approved") {
    return "border-emerald-300 bg-emerald-50 text-emerald-700"
  }
  if (status === "failed" || status === "cancelled" || status === "denied") {
    return "border-red-300 bg-red-50 text-red-700"
  }
  if (status === "running" || status === "queued" || status === "pending") {
    return "border-amber-300 bg-amber-50 text-amber-700"
  }
  return "border-slate-300 bg-slate-50 text-slate-700"
}

function StatusBadge({ value }: { value?: string }) {
  return <Badge variant="outline" className={statusTone(value)}>{value || "unknown"}</Badge>
}

function timeLabel(value?: string | number): string {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function appendMessageText(message: AppendMessage): string {
  return message.content
    .map((part) => part.type === "text" ? part.text : "")
    .join("\n")
    .trim()
}

function copyText(value: unknown) {
  if (typeof navigator === "undefined") return
  const text = typeof value === "string" ? value : truncateJson(value, 4000)
  navigator.clipboard?.writeText(text).catch(() => undefined)
}

function ToolCallCard({ tool }: { tool: FastReactToolBlock }) {
  return (
    <div className="rounded-md border bg-background p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Terminal className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="truncate font-mono text-xs font-medium">{tool.tool_name}</span>
        </div>
        <StatusBadge value={tool.status} />
      </div>
      {tool.tool_call_id && <div className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{tool.tool_call_id}</div>}
      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-muted-foreground">Args</summary>
        <pre className="mt-2 max-h-44 overflow-auto rounded bg-muted p-2 text-xs">{truncateJson(tool.args, 1800)}</pre>
      </details>
      {tool.result !== undefined && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-muted-foreground">Result</summary>
          <pre className="mt-2 max-h-56 overflow-auto rounded bg-muted p-2 text-xs">{truncateJson(tool.result, 2200)}</pre>
        </details>
      )}
      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
        <span>{timeLabel(tool.started_at)}</span>
        {tool.completed_at && <span>done {timeLabel(tool.completed_at)}</span>}
      </div>
    </div>
  )
}

function ApprovalRequestCard({
  approval,
  onResolve,
}: {
  approval: FastReactApprovalBlock
  onResolve: (requestId: string, approved: boolean) => Promise<void> | void
}) {
  const [busy, setBusy] = useState<"approve" | "deny" | "">("")

  async function resolve(approved: boolean) {
    setBusy(approved ? "approve" : "deny")
    try {
      await onResolve(approval.approval_request_id, approved)
    } finally {
      setBusy("")
    }
  }

  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <ShieldQuestion className="h-4 w-4 shrink-0" />
          <span className="truncate font-medium">{approval.tool_name || "Approval required"}</span>
        </div>
        <StatusBadge value={approval.status || "pending"} />
      </div>
      <div className="mt-1 break-all font-mono text-[11px]">{approval.approval_request_id}</div>
      {approval.reason && <div className="mt-2">{approval.reason}</div>}
      <details className="mt-2">
        <summary className="cursor-pointer text-xs">Tool args</summary>
        <pre className="mt-2 max-h-44 overflow-auto rounded bg-white/70 p-2 text-xs">{truncateJson(approval.tool_args, 1800)}</pre>
      </details>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => resolve(true)} disabled={Boolean(busy)}>
          <Check className="mr-2 h-4 w-4" />Approve
        </Button>
        <Button size="sm" variant="outline" onClick={() => resolve(false)} disabled={Boolean(busy)}>
          <X className="mr-2 h-4 w-4" />Deny
        </Button>
      </div>
    </div>
  )
}

function CitationChips({ citations }: { citations: FastReactCitation[] }) {
  if (!citations.length) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {citations.slice(0, 16).map((citation, index) => (
        <button
          key={`${citation.event_id || citation.event_type}-${citation.source_id}-${index}`}
          type="button"
          onClick={() => copyText(citation.metadata || citation)}
          className="inline-flex max-w-full items-center gap-1 rounded-full border bg-background px-2 py-1 text-left text-[11px] text-muted-foreground hover:bg-muted"
          title={truncateJson(citation.metadata || citation, 800)}
        >
          <Clipboard className="h-3 w-3 shrink-0" />
          <span className="truncate">{citation.title || citation.source_id}</span>
        </button>
      ))}
    </div>
  )
}

function MessageBubble({
  message,
  onResolveApproval,
}: {
  message: FastReactThreadMessage
  onResolveApproval: (requestId: string, approved: boolean) => Promise<void> | void
}) {
  const isUser = message.role === "user"
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={cn(
        "w-full max-w-[880px] rounded-md border p-3",
        isUser ? "bg-primary text-primary-foreground" : "bg-card",
      )}>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-medium">
            {isUser ? <MessageSquare className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            {isUser ? "User" : "Assistant"}
          </div>
          {!isUser && <StatusBadge value={message.status} />}
        </div>
        {message.reasoning.length > 0 && (
          <details className="mb-3 rounded border bg-muted/50 p-2 text-xs">
            <summary className="cursor-pointer text-muted-foreground">Reasoning/status</summary>
            <div className="mt-2 space-y-1">
              {message.reasoning.map((item, index) => <div key={`${item}-${index}`} className="whitespace-pre-wrap">{item}</div>)}
            </div>
          </details>
        )}
        {message.content && <div className="whitespace-pre-wrap text-sm leading-6">{message.content}</div>}
        {message.tool_calls.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.tool_calls.map((tool, index) => <ToolCallCard key={`${tool.id}-${index}`} tool={tool} />)}
          </div>
        )}
        {message.approvals.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.approvals.map((approval, index) => (
              <ApprovalRequestCard
                key={`${approval.approval_request_id}-${index}`}
                approval={approval}
                onResolve={onResolveApproval}
              />
            ))}
          </div>
        )}
        <div className="mt-3">
          <CitationChips citations={message.citations} />
        </div>
        {!isUser && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
            <span>{message.events.length} events</span>
            <button type="button" className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => copyText(message.raw_events)}>
              <Copy className="h-3 w-3" />Copy raw
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function AssistantUiRuntimeBoundary({
  snapshot,
  running,
  onSubmit,
  onCancel,
  children,
}: {
  snapshot: ReturnType<typeof fastReactEventsToThreadMessages>
  running: boolean
  onSubmit: (input: string) => Promise<void>
  onCancel: () => Promise<void>
  children: React.ReactNode
}) {
  const runtime = useExternalStoreRuntime({
    messages: snapshot.assistantUiMessages,
    isRunning: running,
    unstable_capabilities: { copy: true },
    onNew: async (message) => {
      const text = appendMessageText(message)
      if (text) await onSubmit(text)
    },
    onCancel,
  })

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ThreadPrimitive.Root className="contents">{children}</ThreadPrimitive.Root>
    </AssistantRuntimeProvider>
  )
}

export function AssistantRunPanel({
  selectedRunId,
  selectedRun,
  events,
  isRunning,
  onRunCreated,
  onRefreshRun,
  onCancelRun,
  onResolveApproval,
  onError,
  onRunningChange,
  onSaveSettings,
}: AssistantRunPanelProps) {
  const [input, setInput] = useState("Summarize the current FastReAct daemon status.")
  const [localRunId, setLocalRunId] = useState("")
  const pollerRef = useRef<number | null>(null)
  const snapshot = useMemo(() => fastReactEventsToThreadMessages(events), [events])
  const activeRunId = selectedRunId || localRunId
  const running = isRunning || selectedRun?.status === "running" || selectedRun?.status === "queued"

  useEffect(() => () => {
    if (pollerRef.current) window.clearInterval(pollerRef.current)
  }, [])

  async function refreshUntilDone(runId: string) {
    if (pollerRef.current) window.clearInterval(pollerRef.current)
    pollerRef.current = window.setInterval(async () => {
      try {
        await onRefreshRun(runId)
        const latest = await serviceJson<RunRecord>(`/v1/runs/${runId}`)
        if (["completed", "failed", "cancelled", "expired"].includes(latest.status)) {
          if (pollerRef.current) window.clearInterval(pollerRef.current)
          pollerRef.current = null
          onRunningChange(false)
          await onRefreshRun(runId)
        }
      } catch (err) {
        if (pollerRef.current) window.clearInterval(pollerRef.current)
        pollerRef.current = null
        onRunningChange(false)
        onError(err instanceof Error ? err.message : String(err))
      }
    }, 1200)
  }

  async function submitFastReactRun(text: string) {
    if (!text.trim()) return
    onSaveSettings()
    onError("")
    onRunningChange(true)
    try {
      const payload = await serviceJson<RunRecord & { run_id: string }>("/v1/runs", {
        method: "POST",
        body: JSON.stringify({
          messages: [{ role: "user", content: text }],
          stream: true,
          metadata: { source: "assistant_ui_service_console" },
        }),
      })
      setLocalRunId(payload.run_id)
      await onRunCreated(payload)
      await onRefreshRun(payload.run_id)
      await refreshUntilDone(payload.run_id)
    } catch (err) {
      onRunningChange(false)
      onError(err instanceof Error ? err.message : String(err))
    }
  }

  async function cancelActiveRun() {
    if (!activeRunId) return
    if (pollerRef.current) window.clearInterval(pollerRef.current)
    pollerRef.current = null
    await onCancelRun(activeRunId)
    onRunningChange(false)
  }

  async function resolveApproval(requestId: string, approved: boolean) {
    await onResolveApproval(requestId, approved)
    if (activeRunId) await onRefreshRun(activeRunId)
  }

  return (
    <AssistantUiRuntimeBoundary
      snapshot={snapshot}
      running={running}
      onSubmit={submitFastReactRun}
      onCancel={cancelActiveRun}
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />Assistant Chat
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              className="min-h-[190px]"
              placeholder="Send a durable FastReAct run"
            />
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => submitFastReactRun(input)} disabled={running || !input.trim()}>
                <Play className="mr-2 h-4 w-4" />Run
              </Button>
              <Button variant="outline" onClick={() => activeRunId && onRefreshRun(activeRunId)} disabled={!activeRunId}>
                <RefreshCw className="mr-2 h-4 w-4" />Refresh
              </Button>
              <Button variant="outline" onClick={cancelActiveRun} disabled={!activeRunId || !running}>
                <StopCircle className="mr-2 h-4 w-4" />Cancel
              </Button>
            </div>
            <div className="rounded-md border p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">Run</span>
                <StatusBadge value={selectedRun?.status || snapshot.status} />
              </div>
              <div className="mt-2 break-all font-mono text-xs text-muted-foreground">{activeRunId || "No run selected"}</div>
              <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                <div>Session: {selectedRun?.session_id || "-"}</div>
                <div>Events: {events.length}</div>
                <div>Created: {timeLabel(selectedRun?.created_at)}</div>
                <div>Duration: {selectedRun?.duration_ms ?? "-"} ms</div>
              </div>
              {(selectedRun?.last_error || selectedRun?.error) && (
                <div className="mt-2 flex gap-2 rounded border border-red-300 bg-red-50 p-2 text-xs text-red-700">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{selectedRun.last_error || selectedRun.error}</span>
                </div>
              )}
            </div>
            <div className="rounded-md border p-3">
              <div className="mb-2 text-sm font-medium">Citations</div>
              <CitationChips citations={snapshot.citations} />
              {!snapshot.citations.length && <div className="text-sm text-muted-foreground">No citations in the current event stream.</div>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-3">
              <span>Run Thread</span>
              <Badge variant="outline">{snapshot.messages.length} messages</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[680px] pr-4">
              <div className="space-y-3">
                {snapshot.messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    onResolveApproval={resolveApproval}
                  />
                ))}
                {!snapshot.messages.length && (
                  <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
                    Create a durable run to see assistant messages, tool calls, approvals, and citations here.
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </AssistantUiRuntimeBoundary>
  )
}
