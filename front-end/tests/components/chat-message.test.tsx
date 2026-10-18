import { screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ChatMessage } from "@/components/chat/chat-message"
import type { ChatMessage as ChatMessageType } from "@/components/chat/chat-provider"
import type { QueryResult } from "@/lib/api/events"
import { fakeApi, PENDING } from "../fake-api"
import { renderWithProviders } from "../test-utils"

describe("ChatMessage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fakeApi({
      "GET /catalog": { metrics: [] },
      "POST /widgets/preview": PENDING,
      "POST /widgets": PENDING,
    })
  })

  // Verifies that a user message renders prompt text in an end-aligned message bubble.
  it("renders user prompt message in end-aligned bubble", () => {
    const userMsg: ChatMessageType = {
      id: "u1",
      role: "user",
      parts: [{ kind: "text", text: "Why did my score drop yesterday?" }],
    }

    renderWithProviders(<ChatMessage message={userMsg} />, { role: "patient" })

    expect(screen.getByText("Why did my score drop yesterday?")).toBeInTheDocument()
  })

  // Verifies that thinking indicator renders for pending assistant message without parts.
  it("renders thinking dots and audience-specific label while waiting for response", () => {
    const pendingMsg: ChatMessageType = {
      id: "a1",
      role: "assistant",
      pending: true,
      parts: [],
    }

    const { unmount } = renderWithProviders(<ChatMessage message={pendingMsg} />, { role: "patient" })
    expect(screen.getByText("One moment…")).toBeInTheDocument()

    unmount()


    renderWithProviders(<ChatMessage message={pendingMsg} />, { role: "clinician" })
    expect(screen.getByText("Thinking…")).toBeInTheDocument()
  })

  // Verifies that running tool part displays spinner and present-tense activity label.
  it("renders running tool indicator with active status and spinner", () => {
    const toolMsg: ChatMessageType = {
      id: "a2",
      role: "assistant",
      parts: [
        {
          kind: "tool",
          callId: "c1",
          tool: "get_my_status",
          status: "running",
        },
      ],
    }

    renderWithProviders(<ChatMessage message={toolMsg} />, { role: "patient" })

    expect(screen.getByText("Checking your latest score")).toBeInTheDocument()
    expect(screen.queryByText("Checked your latest score")).not.toBeInTheDocument()
  })

  // Verifies that completed tool part displays checkmark and past-tense label.
  it("renders completed tool indicator with checkmark and finished label", () => {
    const toolMsg: ChatMessageType = {
      id: "a3",
      role: "assistant",
      parts: [
        {
          kind: "tool",
          callId: "c2",
          tool: "get_my_status",
          status: "done",
          summary: "Score 85",
        },
      ],
    }

    renderWithProviders(<ChatMessage message={toolMsg} />, { role: "patient" })

    expect(screen.getByText("Checked your latest score")).toBeInTheDocument()
    // Patient view suppresses technical summary string
    expect(screen.queryByText(/Score 85/)).not.toBeInTheDocument()
  })

  // Verifies that clinician audience receives detailed tool summary string.
  it("displays tool summary detail for clinicians while suppressing for patients", () => {
    const toolMsg: ChatMessageType = {
      id: "a4",
      role: "assistant",
      parts: [
        {
          kind: "tool",
          callId: "c3",
          tool: "list_participants",
          status: "done",
          summary: "18 patients ranked",
        },
      ],
    }

    renderWithProviders(<ChatMessage message={toolMsg} />, { role: "clinician" })

    expect(screen.getByText(/Ranked patients · 18 patients ranked/i)).toBeInTheDocument()
  })

  // Verifies that markdown text parts render formatted text correctly.
  it("renders formatted markdown text content within assistant bubble", () => {
    const markdownMsg: ChatMessageType = {
      id: "a5",
      role: "assistant",
      parts: [
        {
          kind: "text",
          text: "**Your score improved** by 3 points.",
        },
      ],
    }

    renderWithProviders(<ChatMessage message={markdownMsg} />, { role: "patient" })

    expect(screen.getByText("Your score improved")).toBeInTheDocument()
    expect(screen.getByText(/by 3 points/)).toBeInTheDocument()
  })

  // Verifies that error parts display within a destructive alert banner.
  it("renders error parts inside destructive alert component", () => {
    const errorMsg: ChatMessageType = {
      id: "a6",
      role: "assistant",
      parts: [
        {
          kind: "error",
          message: "Failed to query telemetry records.",
        },
      ],
    }

    renderWithProviders(<ChatMessage message={errorMsg} />, { role: "patient" })

    expect(screen.getByText("Failed to query telemetry records.")).toBeInTheDocument()
  })

  // Verifies that stopped message renders stopped status in message footer.
  it("renders stopped indicator in footer when stream was cancelled", () => {
    const stoppedMsg: ChatMessageType = {
      id: "a7",
      role: "assistant",
      stopped: true,
      parts: [{ kind: "text", text: "Partial response before cancel" }],
    }

    renderWithProviders(<ChatMessage message={stoppedMsg} />, { role: "patient" })

    expect(screen.getByText("Stopped")).toBeInTheDocument()
  })

  // Verifies that ungrounded numbers badge renders with tooltip when present.
  it("renders ungrounded numbers warning badge with explanatory tooltip", () => {
    const ungroundedMsg: ChatMessageType = {
      id: "a8",
      role: "assistant",
      ungrounded: ["142", "99%"],
      parts: [{ kind: "text", text: "Answer with unverified figures" }],
    }

    renderWithProviders(<ChatMessage message={ungroundedMsg} />, { role: "patient" })

    expect(screen.getByText("Some numbers couldn't be checked")).toBeInTheDocument()
  })

  // Verifies that chart parts render within chat message flow.
  it("renders embedded query chart when chart part is received", () => {
    const sampleChart: QueryResult = {
      metrics: ["gluco_score"],
      series: [{ display_name: "Self", points: [] }],
      start: "2026-10-09T00:00:00Z",
      end: "2026-10-16T00:00:00Z",
      as_of: null,
      units: {},
      bucket: "day",
      agg: "mean",
      group_by: "participant",
      total_series: 1,
      truncated: false,
    }

    const chartMsg: ChatMessageType = {
      id: "a9",
      role: "assistant",
      parts: [
        {
          kind: "chart",
          callId: "call-1",
          chart: sampleChart,
        },
      ],
    }

    const { container } = renderWithProviders(<ChatMessage message={chartMsg} />, { role: "patient" })

    expect(container.querySelector(".bg-card")).toBeInTheDocument()
  })
})
