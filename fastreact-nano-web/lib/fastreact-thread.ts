import type { ThreadMessage } from "@assistant-ui/react"

export type FastReactRunEvent = {
  event_id?: string
  sequence?: number
  type: string
  content?: string
  tool_name?: string
  tool_args?: unknown
  tool_call_id?: string
  cited_source_ids?: string[]
  approval_request_id?: string
  metadata?: Record<string, unknown>
  timestamp?: string | number
}

export type FastReactCitation = {
  source_id: string
  event_type: string
  event_id?: string
  title?: string
  url?: string
  snippet?: string
  metadata?: unknown
}

export type FastReactToolBlock = {
  id: string
  tool_call_id?: string
  tool_name: string
  args?: unknown
  result?: unknown
  status: "running" | "complete" | "failed"
  started_at?: string | number
  completed_at?: string | number
  event: FastReactRunEvent
  result_event?: FastReactRunEvent
}

export type FastReactApprovalBlock = {
  id: string
  approval_request_id: string
  tool_name?: string
  tool_args?: unknown
  reason?: string
  status?: string
  event: FastReactRunEvent
}

export type FastReactThreadMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  reasoning: string[]
  status: "running" | "complete" | "failed"
  created_at?: string | number
  events: FastReactRunEvent[]
  tool_calls: FastReactToolBlock[]
  approvals: FastReactApprovalBlock[]
  citations: FastReactCitation[]
  raw_events: FastReactRunEvent[]
}

export type FastReactThreadSnapshot = {
  messages: FastReactThreadMessage[]
  assistantUiMessages: ThreadMessage[]
  events: FastReactRunEvent[]
  citations: FastReactCitation[]
  status: "empty" | "running" | "complete" | "failed"
}

export type FastReactReplayEvent = {
  id: string
  sequence: number
  type: string
  status: "running" | "complete" | "failed" | "requires_action" | "info"
  label: string
  content?: string
  event: FastReactRunEvent
  tool?: FastReactToolBlock
  approval?: FastReactApprovalBlock
  citations: FastReactCitation[]
}

export type FastReactTraceSummary = {
  final_content: string
  error: string
  tool_call_count: number
  approval_count: number
  compression_count: number
  policy_snapshot_hash: string
  llm_usage_total?: Record<string, unknown>
  pska_digest_tool_budget?: unknown
}

export type FastReactReplaySnapshot = {
  events: FastReactRunEvent[]
  replayEvents: FastReactReplayEvent[]
  toolCalls: FastReactToolBlock[]
  approvals: FastReactApprovalBlock[]
  citations: FastReactCitation[]
  summary: FastReactTraceSummary
}

export function eventKey(event: FastReactRunEvent, fallback: number): string {
  return event.event_id || `${event.type}-${event.sequence ?? fallback}`
}

export function textFromUnknown(value: unknown): string {
  if (typeof value === "string") return value
  if (value == null) return ""
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null
}

function findString(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === "string" && value.trim()) return value
  }
  return ""
}

function addCitation(
  citations: Map<string, FastReactCitation>,
  event: FastReactRunEvent,
  source: unknown,
  prefix: string,
) {
  if (typeof source === "string") {
    if (!source.trim()) return
    citations.set(`${eventKey(event, citations.size)}:${prefix}:${source}`, {
      source_id: source,
      event_type: event.type,
      event_id: event.event_id,
      metadata: event.metadata,
    })
    return
  }

  const record = asRecord(source)
  if (!record) return
  const sourceId = findString(record, ["source_id", "sourceId", "id", "url", "title", "path"])
  if (!sourceId) return
  citations.set(`${eventKey(event, citations.size)}:${prefix}:${sourceId}`, {
    source_id: sourceId,
    event_type: event.type,
    event_id: event.event_id,
    title: findString(record, ["title", "name", "filename"]) || undefined,
    url: findString(record, ["url", "uri", "path"]) || undefined,
    snippet: findString(record, ["snippet", "text", "content", "summary"]) || undefined,
    metadata: record,
  })
}

function collectNestedSourceRefs(
  citations: Map<string, FastReactCitation>,
  event: FastReactRunEvent,
  value: unknown,
  depth = 0,
) {
  if (depth > 5 || value == null) return
  if (Array.isArray(value)) {
    for (const item of value) collectNestedSourceRefs(citations, event, item, depth + 1)
    return
  }
  const record = asRecord(value)
  if (!record) return
  for (const key of ["source_refs", "sourceRefs", "sources", "citations", "evidence"]) {
    const nested = record[key]
    if (Array.isArray(nested)) {
      for (const item of nested) addCitation(citations, event, item, key)
    }
  }
  for (const nested of Object.values(record)) {
    if (nested && typeof nested === "object") collectNestedSourceRefs(citations, event, nested, depth + 1)
  }
}

export function collectFastReactCitations(events: readonly FastReactRunEvent[]): FastReactCitation[] {
  const citations = new Map<string, FastReactCitation>()
  for (const event of events) {
    for (const sourceId of event.cited_source_ids || []) addCitation(citations, event, sourceId, "cited")
    const metadata = event.metadata || {}
    for (const key of ["citations", "evidence", "source_refs", "sourceRefs", "sources"]) {
      const values = metadata[key]
      if (Array.isArray(values)) {
        for (const value of values) addCitation(citations, event, value, key)
      }
    }
    collectNestedSourceRefs(citations, event, metadata)
  }
  return [...citations.values()]
}

function toolResultFromEvent(event: FastReactRunEvent): unknown {
  const metadata = event.metadata || {}
  if ("result" in metadata) return metadata.result
  if ("tool_result" in metadata) return metadata.tool_result
  if ("output" in metadata) return metadata.output
  if (event.content) return event.content
  return metadata
}

function ensureAssistant(messages: FastReactThreadMessage[], event: FastReactRunEvent, fallback: number): FastReactThreadMessage {
  const last = messages[messages.length - 1]
  if (last?.role === "assistant") return last
  const message: FastReactThreadMessage = {
    id: `assistant-${eventKey(event, fallback)}`,
    role: "assistant",
    content: "",
    reasoning: [],
    status: "running",
    created_at: event.timestamp,
    events: [],
    tool_calls: [],
    approvals: [],
    citations: [],
    raw_events: [],
  }
  messages.push(message)
  return message
}

function attachEvent(message: FastReactThreadMessage, event: FastReactRunEvent) {
  message.events.push(event)
  message.raw_events.push(event)
}

function matchTool(tool: FastReactToolBlock, event: FastReactRunEvent): boolean {
  if (event.tool_call_id && tool.tool_call_id === event.tool_call_id) return true
  return !tool.result_event && Boolean(event.tool_name) && tool.tool_name === event.tool_name
}

export function mergeFastReactEvents(
  existing: readonly FastReactRunEvent[],
  incoming: readonly FastReactRunEvent[],
): FastReactRunEvent[] {
  const byKey = new Map<string, FastReactRunEvent>()
  for (const event of [...existing, ...incoming]) {
    byKey.set(eventKey(event, byKey.size), event)
  }
  return [...byKey.values()].sort((left, right) => {
    const leftSequence = typeof left.sequence === "number" ? left.sequence : Number.MAX_SAFE_INTEGER
    const rightSequence = typeof right.sequence === "number" ? right.sequence : Number.MAX_SAFE_INTEGER
    if (leftSequence !== rightSequence) return leftSequence - rightSequence
    return eventKey(left, 0).localeCompare(eventKey(right, 0))
  })
}

export function buildFastReactReplay(events: readonly FastReactRunEvent[], trace?: Record<string, unknown> | null): FastReactReplaySnapshot {
  const ordered = mergeFastReactEvents([], events)
  const toolCalls: FastReactToolBlock[] = []
  const approvals: FastReactApprovalBlock[] = []
  const replayEvents: FastReactReplayEvent[] = []

  for (const [index, event] of ordered.entries()) {
    const sequence = typeof event.sequence === "number" ? event.sequence : index
    const citations = collectFastReactCitations([event])
    let label = event.type
    let status: FastReactReplayEvent["status"] = "info"
    let tool: FastReactToolBlock | undefined
    let approval: FastReactApprovalBlock | undefined

    if (event.type === "tool_call") {
      tool = {
        id: eventKey(event, index),
        tool_call_id: event.tool_call_id || findString(event.metadata || {}, ["tool_call_id", "id"]),
        tool_name: event.tool_name || findString(event.metadata || {}, ["tool_name", "name"]) || "tool",
        args: event.tool_args ?? event.metadata?.args,
        status: "running",
        started_at: event.timestamp,
        event,
      }
      toolCalls.push(tool)
      label = tool.tool_name
      status = "running"
    } else if (event.type === "tool_result") {
      tool = [...toolCalls].reverse().find((item) => matchTool(item, event))
      if (tool) {
        tool.result = toolResultFromEvent(event)
        tool.status = event.metadata?.is_error || event.metadata?.error ? "failed" : "complete"
        tool.completed_at = event.timestamp
        tool.result_event = event
        status = tool.status === "failed" ? "failed" : "complete"
        label = tool.tool_name
      } else {
        status = event.metadata?.is_error || event.metadata?.error ? "failed" : "complete"
        label = event.tool_name || "tool_result"
      }
    } else if (event.type === "ask_user" || event.approval_request_id) {
      approval = {
        id: eventKey(event, index),
        approval_request_id: event.approval_request_id || findString(event.metadata || {}, ["approval_request_id", "request_id", "id"]),
        tool_name: event.tool_name,
        tool_args: event.tool_args,
        reason: event.content || findString(event.metadata || {}, ["reason", "message"]),
        status: findString(event.metadata || {}, ["status"]),
        event,
      }
      approvals.push(approval)
      label = approval.tool_name || "approval"
      status = "requires_action"
    } else if (event.type === "error") {
      status = "failed"
    } else if (event.type === "session_end") {
      status = "complete"
    } else if (event.metadata?.compression || event.metadata?.compression_event) {
      label = "context_compression"
      status = "info"
    }

    replayEvents.push({
      id: eventKey(event, index),
      sequence,
      type: event.type,
      status,
      label,
      content: event.content,
      event,
      tool,
      approval,
      citations,
    })
  }

  const finalEvent = [...ordered].reverse().find((event) => event.type === "session_end")
  const errorEvent = [...ordered].reverse().find((event) => event.type === "error")
  const compressionCount = ordered.filter((event) => event.metadata?.compression || event.metadata?.compression_event).length
  const traceRecord = trace || {}
  const summary: FastReactTraceSummary = {
    final_content: textFromUnknown(traceRecord.final_content) || textFromUnknown(traceRecord.final_answer) || finalEvent?.content || "",
    error: textFromUnknown(traceRecord.error) || textFromUnknown(traceRecord.error_summary) || errorEvent?.content || "",
    tool_call_count: Number(traceRecord.tool_call_count ?? toolCalls.length) || 0,
    approval_count: Number(traceRecord.approval_count ?? approvals.length) || 0,
    compression_count: Number(traceRecord.compression_count ?? compressionCount) || 0,
    policy_snapshot_hash: textFromUnknown(traceRecord.policy_snapshot_hash),
    llm_usage_total: asRecord(traceRecord.llm_usage_total) || undefined,
    pska_digest_tool_budget: traceRecord.pska_digest_tool_budget,
  }

  return {
    events: ordered,
    replayEvents,
    toolCalls,
    approvals,
    citations: collectFastReactCitations(ordered),
    summary,
  }
}

function toAssistantUiMessages(messages: FastReactThreadMessage[]): ThreadMessage[] {
  return messages.map((message) => {
    const createdAt = message.created_at ? new Date(message.created_at) : new Date()
    const custom = {
      fastreact: {
        events: message.raw_events,
        tool_calls: message.tool_calls,
        approvals: message.approvals,
        citations: message.citations,
      },
    }
    if (message.role === "user") {
      return {
        id: message.id,
        role: "user",
        createdAt,
        content: [{ type: "text", text: message.content }],
        attachments: [],
        metadata: { custom },
      } satisfies ThreadMessage
    }

    const content = [
      ...message.reasoning.map((text) => ({ type: "reasoning" as const, text })),
      ...message.tool_calls.map((tool) => ({
        type: "tool-call" as const,
        toolCallId: tool.tool_call_id || tool.id,
        toolName: tool.tool_name,
        args: (asRecord(tool.args) || {}) as any,
        argsText: textFromUnknown(tool.args),
        result: tool.result,
        isError: tool.status === "failed",
      })),
      ...message.citations.slice(0, 12).map((citation) => ({
        type: "source" as const,
        sourceType: citation.url ? "url" as const : "document" as const,
        id: citation.source_id,
        url: citation.url,
        title: citation.title || citation.source_id,
        mediaType: citation.url ? undefined : "application/json",
        providerMetadata: { fastreact: { event_type: citation.event_type } },
      })),
      { type: "text" as const, text: message.content || (message.status === "running" ? "Running..." : "") },
    ] as any

    return {
      id: message.id,
      role: "assistant",
      createdAt,
      content,
      status: message.status === "failed"
        ? { type: "incomplete", reason: "error" as const, error: message.content || "Run failed" }
        : message.status === "complete"
          ? { type: "complete", reason: "stop" as const }
          : { type: "running" as const },
      metadata: {
        unstable_state: null,
        unstable_annotations: [],
        unstable_data: [],
        steps: [],
        custom,
      },
    } satisfies ThreadMessage
  })
}

export function fastReactEventsToThreadMessages(events: readonly FastReactRunEvent[]): FastReactThreadSnapshot {
  const messages: FastReactThreadMessage[] = []
  for (const [index, event] of events.entries()) {
    if (event.type === "session_start") {
      const userContent =
        event.content ||
        textFromUnknown(event.metadata?.input || event.metadata?.messages || event.metadata?.request) ||
        "Run started"
      const user: FastReactThreadMessage = {
        id: `user-${eventKey(event, index)}`,
        role: "user",
        content: userContent,
        reasoning: [],
        status: "complete",
        created_at: event.timestamp,
        events: [event],
        tool_calls: [],
        approvals: [],
        citations: [],
        raw_events: [event],
      }
      messages.push(user)
      continue
    }

    const assistant = ensureAssistant(messages, event, index)
    attachEvent(assistant, event)

    if (event.type === "think" && event.content) {
      assistant.reasoning.push(event.content)
    } else if (event.type === "tool_call") {
      assistant.tool_calls.push({
        id: eventKey(event, index),
        tool_call_id: event.tool_call_id || findString(event.metadata || {}, ["tool_call_id", "id"]),
        tool_name: event.tool_name || findString(event.metadata || {}, ["tool_name", "name"]) || "tool",
        args: event.tool_args ?? event.metadata?.args,
        status: "running",
        started_at: event.timestamp,
        event,
      })
    } else if (event.type === "tool_result") {
      const tool = [...assistant.tool_calls].reverse().find((item) => matchTool(item, event))
      if (tool) {
        tool.result = toolResultFromEvent(event)
        tool.status = event.metadata?.is_error || event.metadata?.error ? "failed" : "complete"
        tool.completed_at = event.timestamp
        tool.result_event = event
      }
    } else if (event.type === "ask_user" || event.approval_request_id) {
      assistant.approvals.push({
        id: eventKey(event, index),
        approval_request_id: event.approval_request_id || findString(event.metadata || {}, ["approval_request_id", "request_id", "id"]),
        tool_name: event.tool_name,
        tool_args: event.tool_args,
        reason: event.content || findString(event.metadata || {}, ["reason", "message"]),
        status: findString(event.metadata || {}, ["status"]),
        event,
      })
      assistant.status = "running"
    } else if (event.type === "session_end") {
      assistant.content = event.content || textFromUnknown(event.metadata?.final || event.metadata?.final_content) || assistant.content
      assistant.status = "complete"
    } else if (event.type === "error") {
      assistant.content = event.content || textFromUnknown(event.metadata?.error) || "Run failed"
      assistant.status = "failed"
    } else if (event.content && !assistant.content) {
      assistant.content = event.content
    }
  }

  for (const message of messages) {
    message.citations = collectFastReactCitations(message.raw_events)
  }
  const citations = collectFastReactCitations(events)
  const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant")
  const status = !messages.length ? "empty" : lastAssistant?.status || "complete"
  return {
    messages,
    assistantUiMessages: toAssistantUiMessages(messages),
    events: [...events],
    citations,
    status,
  }
}
