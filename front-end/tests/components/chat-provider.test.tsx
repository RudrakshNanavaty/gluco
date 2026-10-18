import { QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { ChatProvider, useChat } from "@/components/chat/chat-provider"
import { fakeApi } from "../fake-api"
import { createTestQueryClient } from "../test-utils"

const CHART = {
  as_of: null,
  start: null,
  end: null,
  metrics: ["gluco_score"],
  units: {},
  bucket: "hour",
  agg: "mean",
  group_by: "participant",
  series: [{ display_name: "Patient 013", points: [] }],
  total_series: 1,
  truncated: false,
}
const WIDGET = { title: "My week", kind: "trend", query: {}, steps: [] }

// One assistant turn, as the stream sends it and as the transcript returns it.
const TURN = [
  { type: "tool_start", call_id: "c1", tool: "build_my_widget", args: {} },
  { type: "tool_end", call_id: "c1", tool: "build_my_widget", summary: "Built", rows: 1 },
  { type: "data", call_id: "c1", tool: "build_my_widget", chart: CHART, widget: WIDGET },
  { type: "token", text: "Here is your week." },
]

function renderChat() {
  const queryClient = createTestQueryClient()
  return renderHook(() => useChat(), {
    wrapper: ({ children }) => (
      <QueryClientProvider client={queryClient}>
        <ChatProvider>{children}</ChatProvider>
      </QueryClientProvider>
    ),
  }).result
}

function stream(events: object[]) {
  const body = events
    .map((e) => `event: ${(e as { type: string }).type}\ndata: ${JSON.stringify(e)}\n\n`)
    .join("")
  return new Response(body, { headers: { "Content-Type": "text/event-stream" } })
}

describe("ChatProvider", () => {
  // Verifies a reopened thread keeps its charts and widgets, rebuilt by the live reducer.
  it("restores a thread's tool steps, chart and widget from the server", async () => {
    fakeApi({
      "GET /chat/sessions/{session_id}": [
        { role: "user", text: "Show my week" },
        { role: "assistant", events: TURN },
      ],
    })
    const chat = renderChat()

    await act(() => chat.current.openThread("t1"))

    const answer = chat.current.messages[1]
    expect(answer.parts.map((p) => p.kind)).toEqual(["tool", "chart", "text"])
    expect(answer.parts[1]).toMatchObject({ kind: "chart", widget: WIDGET })
  })

  // Verifies a live answer and the same answer restored end up identical.
  it("builds the same message live as it restores later", async () => {
    fakeApi({
      "POST /chat": () => stream([...TURN, { type: "done", session_id: "s" }]),
      "GET /chat/sessions": [],
      "GET /chat/sessions/{session_id}": [
        { role: "user", text: "Show my week" },
        { role: "assistant", events: TURN },
      ],
    })
    const chat = renderChat()

    act(() => chat.current.send("Show my week"))
    await waitFor(() => expect(chat.current.messages[1]?.pending).toBe(false))
    const live = chat.current.messages[1].parts
    expect(live.map((p) => p.kind)).toEqual(["tool", "chart", "text"])

    await act(() => chat.current.openThread("t1"))

    expect(chat.current.messages[1].parts).toEqual(live)
  })
})
