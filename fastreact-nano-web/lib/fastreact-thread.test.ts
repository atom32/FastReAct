import { describe, expect, it } from "vitest"
import { fastReactEventsToThreadMessages } from "./fastreact-thread"

describe("fastReactEventsToThreadMessages", () => {
  it("merges tool_call and tool_result into one tool card", () => {
    const snapshot = fastReactEventsToThreadMessages([
      { type: "session_start", content: "inspect workspace", sequence: 1 },
      { type: "tool_call", tool_call_id: "call_1", tool_name: "exec", tool_args: { command: "pwd" }, sequence: 2 },
      { type: "tool_result", tool_call_id: "call_1", tool_name: "exec", content: "/tmp/project", sequence: 3 },
    ])

    const assistant = snapshot.messages.find((message) => message.role === "assistant")
    expect(assistant?.tool_calls).toHaveLength(1)
    expect(assistant?.tool_calls[0]).toMatchObject({
      tool_call_id: "call_1",
      tool_name: "exec",
      result: "/tmp/project",
      status: "complete",
    })
  })

  it("maps ask_user to an approval card and preserves approval_request_id", () => {
    const snapshot = fastReactEventsToThreadMessages([
      { type: "session_start", content: "write a file", sequence: 1 },
      {
        type: "ask_user",
        approval_request_id: "apr_123",
        tool_name: "write_file",
        tool_args: { path: "README.md" },
        content: "write_file requires approval",
        sequence: 2,
      },
    ])

    const assistant = snapshot.messages.find((message) => message.role === "assistant")
    expect(assistant?.approvals[0]).toMatchObject({
      approval_request_id: "apr_123",
      tool_name: "write_file",
      reason: "write_file requires approval",
    })
  })

  it("uses session_end as the final assistant message", () => {
    const snapshot = fastReactEventsToThreadMessages([
      { type: "session_start", content: "hello", sequence: 1 },
      { type: "think", content: "thinking", sequence: 2 },
      { type: "session_end", content: "done", sequence: 3 },
    ])

    const assistant = snapshot.messages.find((message) => message.role === "assistant")
    expect(assistant?.content).toBe("done")
    expect(assistant?.status).toBe("complete")
    expect(assistant?.reasoning).toEqual(["thinking"])
  })

  it("marks error events as failed assistant state", () => {
    const snapshot = fastReactEventsToThreadMessages([
      { type: "session_start", content: "break", sequence: 1 },
      { type: "error", content: "tool failed", sequence: 2 },
    ])

    const assistant = snapshot.messages.find((message) => message.role === "assistant")
    expect(assistant?.status).toBe("failed")
    expect(assistant?.content).toBe("tool failed")
    expect(snapshot.status).toBe("failed")
  })

  it("preserves PSKA citation and source ref metadata", () => {
    const snapshot = fastReactEventsToThreadMessages([
      { type: "session_start", content: "digest", sequence: 1 },
      {
        type: "tool_result",
        tool_name: "pska_pska_write_candidates",
        cited_source_ids: ["src_direct"],
        metadata: {
          result: {
            candidates: [
              {
                text: "memory",
                source_refs: [{ source_id: "src_nested", title: "Notebook", snippet: "orchid-lattice" }],
              },
            ],
          },
          evidence: [{ source_id: "src_evidence", url: "file:///tmp/a.md" }],
        },
        sequence: 2,
      },
    ])

    expect(snapshot.citations.map((citation) => citation.source_id)).toEqual(
      expect.arrayContaining(["src_direct", "src_evidence", "src_nested"]),
    )
    expect(snapshot.events[1].metadata).toMatchObject({ result: expect.any(Object) })
  })
})
