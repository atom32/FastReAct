"use client"

import { useEffect, useMemo, useState } from "react"
import { AlertTriangle, Check, ChevronDown, Clipboard, Copy, Filter, RefreshCw, ShieldQuestion, StopCircle, Terminal, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { serviceJson, stringifyJson, truncateJson } from "@/lib/service-api"
import {
  buildFastReactReplay,
  eventKey,
  mergeFastReactEvents,
  type FastReactApprovalBlock,
  type FastReactCitation,
  type FastReactReplayEvent,
  type FastReactRunEvent,
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

type EventPage = {
  events: FastReactRunEvent[]
  next_after_sequence?: number | null
  has_more?: boolean
}

type RunTraceWorkbenchProps = {
  runs: RunRecord[]
  traces: RunRecord[]
  selectedRunId: string
  selectedRun?: RunRecord | null
  runDetail?: RunRecord | null
  traceDetail?: Record<string, unknown> | null
  events: FastReactRunEvent[]
  onSelectRun: (runId: string) => void
  onRefreshRuns: () => Promise<void> | void
  onRefreshRun: (runId: string) => Promise<void> | void
  onCancelRun: (runId: string) => Promise<void> | void
  onResolveApproval: (requestId: string, approved: boolean) => Promise<void> | void
  onError: (message: string) => void
}

const STATUS_FILTERS = ["all", "queued", "running", "completed", "failed", "cancelled", "expired"] as const
const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled", "expired"])

function statusTone(status?: string): string {
  if (status === "completed" || status === "complete" || status === "approved") {
    return "border-emerald-300 bg-emerald-50 text-emerald-700"
  }
  if (status === "failed" || status === "cancelled" || status === "denied" || status === "expired") {
    return "border-red-300 bg-red-50 text-red-700"
  }
  if (status === "running" || status === "queued" || status === "pending" || status === "requires_action") {
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
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function copyText(value: unknown) {
  if (typeof navigator === "undefined") return
  const text = stringifyJson(value)
  navigator.clipboard?.writeText(text).catch(() => undefined)
}

function shortId(value?: string): string {
  return value ? value.slice(0, 13) : "-"
}

function MetricTile({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-md border p-2 text-sm">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 break-all font-medium">{value == null || value === "" ? "-" : String(value)}</div>
    </div>
  )
}

function CitationChips({ citations }: { citations: FastReactCitation[] }) {
  if (!citations.length) return <div className="text-sm text-muted-foreground">No citation or evidence metadata in this replay.</div>
  return (
    <div className="flex flex-wrap gap-1.5">
      {citations.slice(0, 24).map((citation, index) => (
        <button
          key={`${citation.event_id || citation.event_type}-${citation.source_id}-${index}`}
          type="button"
          onClick={() => copyText(citation.metadata || citation)}
          className="inline-flex max-w-full items-center gap-1 rounded-full border bg-background px-2 py-1 text-left text-[11px] text-muted-foreground hover:bg-muted"
          title={truncateJson(citation.metadata || citation, 900)}
        >
          <Clipboard className="h-3 w-3 shrink-0" />
          <span className="truncate">{citation.title || citation.source_id}</span>
        </button>
      ))}
    </div>
  )
}

function ToolReplayCard({ tool }: { tool: FastReactToolBlock }) {
  return (
    <div className="mt-2 rounded-md border bg-background p-3">
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
        <pre className="mt-2 max-h-44 overflow-auto rounded bg-muted p-2 text-xs">{truncateJson(tool.args, 2200)}</pre>
      </details>
      {tool.result !== undefined && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-muted-foreground">Result</summary>
          <pre className="mt-2 max-h-56 overflow-auto rounded bg-muted p-2 text-xs">{truncateJson(tool.result, 2600)}</pre>
        </details>
      )}
    </div>
  )
}

function ApprovalReplayCard({
  approval,
  onResolveApproval,
}: {
  approval: FastReactApprovalBlock
  onResolveApproval: (requestId: string, approved: boolean) => Promise<void> | void
}) {
  const [busy, setBusy] = useState<"approve" | "deny" | "">("")
  async function resolve(approved: boolean) {
    setBusy(approved ? "approve" : "deny")
    try {
      await onResolveApproval(approval.approval_request_id, approved)
    } finally {
      setBusy("")
    }
  }

  return (
    <div className="mt-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-950">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <ShieldQuestion className="h-4 w-4 shrink-0" />
          <span className="truncate font-medium">{approval.tool_name || "Approval required"}</span>
        </div>
        <StatusBadge value={approval.status || "pending"} />
      </div>
      <div className="mt-1 break-all font-mono text-[11px]">{approval.approval_request_id}</div>
      {approval.reason && <div className="mt-2 text-sm">{approval.reason}</div>}
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

function ReplayEventCard({
  replayEvent,
  onResolveApproval,
}: {
  replayEvent: FastReactReplayEvent
  onResolveApproval: (requestId: string, approved: boolean) => Promise<void> | void
}) {
  const isCompression = Boolean(replayEvent.event.metadata?.compression || replayEvent.event.metadata?.compression_event)
  return (
    <div className={cn("rounded-md border p-3 text-sm", replayEvent.status === "failed" && "border-red-300 bg-red-50")}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Badge variant="secondary">{replayEvent.sequence}</Badge>
          <span className="truncate font-medium">{isCompression ? "context_compression" : replayEvent.type}</span>
          {replayEvent.label !== replayEvent.type && <Badge variant="outline">{replayEvent.label}</Badge>}
        </div>
        <StatusBadge value={replayEvent.status} />
      </div>
      {replayEvent.content && <div className="whitespace-pre-wrap leading-6">{replayEvent.content}</div>}
      {replayEvent.tool && replayEvent.type === "tool_call" && <ToolReplayCard tool={replayEvent.tool} />}
      {replayEvent.approval && <ApprovalReplayCard approval={replayEvent.approval} onResolveApproval={onResolveApproval} />}
      <div className="mt-2">
        <CitationChips citations={replayEvent.citations} />
      </div>
      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-muted-foreground">Raw event</summary>
        <pre className="mt-2 max-h-56 overflow-auto rounded bg-muted p-2 text-xs">{truncateJson(replayEvent.event, 2600)}</pre>
      </details>
    </div>
  )
}

function RunListItem({
  run,
  selected,
  onSelect,
}: {
  run: RunRecord
  selected: boolean
  onSelect: () => void
}) {
  const error = run.last_error || run.error
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn("w-full rounded-md border p-3 text-left text-sm hover:bg-muted", selected && "border-primary bg-muted")}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs">{shortId(run.run_id)}</span>
        <StatusBadge value={run.status} />
      </div>
      <div className="mt-2 grid gap-1 text-xs text-muted-foreground">
        <span>created {timeLabel(run.created_at)}</span>
        <span>completed {timeLabel(run.completed_at)} · {run.duration_ms ?? "-"} ms · {run.event_count ?? 0} events</span>
      </div>
      {error && <div className="mt-2 line-clamp-2 text-xs text-red-700">{error}</div>}
    </button>
  )
}

export function RunTraceWorkbench({
  runs,
  traces,
  selectedRunId,
  selectedRun,
  runDetail,
  traceDetail,
  events,
  onSelectRun,
  onRefreshRuns,
  onRefreshRun,
  onCancelRun,
  onResolveApproval,
  onError,
}: RunTraceWorkbenchProps) {
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>("all")
  const [replayEvents, setReplayEvents] = useState<FastReactRunEvent[]>(events)
  const [nextAfterSequence, setNextAfterSequence] = useState<number | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const selected = runDetail || selectedRun || null
  const replay = useMemo(() => buildFastReactReplay(replayEvents, traceDetail), [replayEvents, traceDetail])
  const filteredRuns = useMemo(
    () => statusFilter === "all" ? runs : runs.filter((run) => run.status === statusFilter),
    [runs, statusFilter],
  )
  const traceByRunId = useMemo(() => new Map(traces.map((trace) => [trace.run_id, trace])), [traces])

  useEffect(() => {
    setReplayEvents(events)
    const lastSequence = events.reduce<number | null>((latest, event) => {
      if (typeof event.sequence !== "number") return latest
      return latest == null || event.sequence > latest ? event.sequence : latest
    }, null)
    setNextAfterSequence(lastSequence)
    setHasMore(Boolean(selected?.event_count && lastSequence != null && selected.event_count > events.length))
  }, [events, selected?.event_count, selectedRunId])

  async function refreshSelected() {
    await onRefreshRuns()
    if (selectedRunId) await onRefreshRun(selectedRunId)
  }

  async function loadMoreEvents() {
    if (!selectedRunId || nextAfterSequence == null) return
    setLoadingMore(true)
    try {
      const runPath = `/v1/runs/${selectedRunId}/events?limit=200&after_sequence=${nextAfterSequence}`
      let payload: EventPage
      try {
        payload = await serviceJson<EventPage>(runPath)
      } catch {
        payload = await serviceJson<EventPage>(`/v1/traces/${selectedRunId}/events?limit=200&after_sequence=${nextAfterSequence}`)
      }
      setReplayEvents((current) => mergeFastReactEvents(current, payload.events || []))
      setNextAfterSequence(payload.next_after_sequence ?? null)
      setHasMore(Boolean(payload.has_more))
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoadingMore(false)
    }
  }

  async function cancelSelected() {
    if (!selectedRunId) return
    await onCancelRun(selectedRunId)
    await refreshSelected()
  }

  async function resolveApproval(requestId: string, approved: boolean) {
    await onResolveApproval(requestId, approved)
    if (selectedRunId) await onRefreshRun(selectedRunId)
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[380px_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2">
            <span>Runs</span>
            <Button size="sm" variant="outline" onClick={refreshSelected}>
              <RefreshCw className="mr-2 h-4 w-4" />Refresh
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as (typeof STATUS_FILTERS)[number])}
              className="h-9 w-full rounded-md border bg-background px-3 text-sm"
            >
              {STATUS_FILTERS.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </div>
          <div className="grid gap-2 text-sm">
            <MetricTile label="Visible" value={`${filteredRuns.length} / ${runs.length}`} />
          </div>
          <ScrollArea className="h-[720px] pr-3">
            <div className="space-y-2">
              {filteredRuns.map((run, index) => (
                <RunListItem
                  key={`${run.run_id}-${index}`}
                  run={run}
                  selected={run.run_id === selectedRunId}
                  onSelect={() => onSelectRun(run.run_id)}
                />
              ))}
              {!filteredRuns.length && <div className="rounded-md border p-3 text-sm text-muted-foreground">No runs match this status.</div>}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center justify-between gap-3">
              <span>Trace Detail</span>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => selectedRunId && copyText(selectedRunId)} disabled={!selectedRunId}>
                  <Copy className="mr-2 h-4 w-4" />Copy Run ID
                </Button>
                <Button size="sm" variant="outline" onClick={cancelSelected} disabled={!selectedRunId || TERMINAL_STATUSES.has(selected?.status || "")}>
                  <StopCircle className="mr-2 h-4 w-4" />Cancel
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {selected ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="break-all font-mono text-xs">{selected.run_id}</div>
                  <StatusBadge value={selected.status} />
                </div>
                <div className="grid gap-2 md:grid-cols-3">
                  <MetricTile label="Session" value={selected.session_id || "-"} />
                  <MetricTile label="Events" value={selected.event_count ?? replay.events.length} />
                  <MetricTile label="Duration" value={`${selected.duration_ms ?? traceDetail?.duration_ms ?? "-"} ms`} />
                  <MetricTile label="Tool calls" value={replay.summary.tool_call_count} />
                  <MetricTile label="Approvals" value={replay.summary.approval_count} />
                  <MetricTile label="Compression" value={replay.summary.compression_count} />
                </div>
                {replay.summary.policy_snapshot_hash && (
                  <div className="rounded-md border p-2 text-xs">
                    Policy snapshot: <span className="font-mono">{replay.summary.policy_snapshot_hash}</span>
                  </div>
                )}
                {(selected.last_error || selected.error || replay.summary.error) && (
                  <div className="flex gap-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span>{selected.last_error || selected.error || replay.summary.error}</span>
                  </div>
                )}
                {replay.summary.final_content && (
                  <div>
                    <div className="mb-1 text-sm font-medium">Final Content</div>
                    <div className="max-h-[240px] overflow-auto rounded-md border p-3 text-sm whitespace-pre-wrap">{replay.summary.final_content}</div>
                  </div>
                )}
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-md border p-3">
                    <div className="mb-2 text-sm font-medium">LLM Usage</div>
                    <pre className="max-h-[180px] overflow-auto rounded bg-muted p-2 text-xs">{truncateJson(replay.summary.llm_usage_total || {}, 1000)}</pre>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="mb-2 text-sm font-medium">PSKA Digest Budget</div>
                    <pre className="max-h-[180px] overflow-auto rounded bg-muted p-2 text-xs">{truncateJson(replay.summary.pska_digest_tool_budget || traceByRunId.get(selected.run_id)?.metadata || {}, 1200)}</pre>
                  </div>
                </div>
                <div className="rounded-md border p-3">
                  <div className="mb-2 text-sm font-medium">Citations</div>
                  <CitationChips citations={replay.citations} />
                </div>
              </>
            ) : (
              <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">Select a run to inspect trace details.</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center justify-between gap-3">
              <span>Event Replay</span>
              <Badge variant="outline">{replay.replayEvents.length} events</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <ScrollArea className="h-[740px] pr-4">
              <div className="space-y-2">
                {replay.replayEvents.map((event) => (
                  <ReplayEventCard
                    key={event.id}
                    replayEvent={event}
                    onResolveApproval={resolveApproval}
                  />
                ))}
                {!replay.replayEvents.length && <div className="rounded-md border p-3 text-sm text-muted-foreground">No durable events loaded for this run.</div>}
              </div>
            </ScrollArea>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-xs text-muted-foreground">
                Next sequence: {nextAfterSequence ?? "-"} · durable pagination: {hasMore ? "more available" : "complete"}
              </div>
              <Button variant="outline" onClick={loadMoreEvents} disabled={!hasMore || loadingMore}>
                <ChevronDown className="mr-2 h-4 w-4" />Load more events
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
