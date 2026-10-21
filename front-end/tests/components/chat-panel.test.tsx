import { fireEvent, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ChatLauncher } from "@/components/chat/chat-launcher"
import { ChatPanel } from "@/components/chat/chat-panel"
import { useChat } from "@/components/chat/chat-provider"
import { useMediaQuery } from "@/hooks/use-media-query"
import { fakeApi, Reply } from "../fake-api"
import { renderWithProviders } from "../test-utils"

vi.mock("@/components/chat/chat-provider", () => ({
  useChat: vi.fn(),
}))

vi.mock("@/hooks/use-media-query", () => ({
  useMediaQuery: vi.fn(),
}))

describe("ChatPanel & Composer", () => {
  const mockSend = vi.fn()
  const mockStop = vi.fn()
  const mockNewChat = vi.fn()
  const mockOpenThread = vi.fn()

  const baseChatState = {
    sessionId: "session-1",
    messages: [],
    streaming: false,
    loadingThread: false,
    send: mockSend,
    stop: mockStop,
    newChat: mockNewChat,
    openThread: mockOpenThread,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useChat).mockReturnValue(
      baseChatState as unknown as ReturnType<typeof useChat>
    )
    fakeApi({
      "GET /catalog": { metrics: [] },
      "GET /widgets": [],
      "GET /chat/sessions": [
        {
          session_id: "session-1",
          title: "Current Chat",
          created_at: "2026-10-16T10:00:00Z",
        },
        {
          session_id: "session-2",
          title: "Yesterday Insights",
          created_at: "2026-10-15T10:00:00Z",
        },
      ],
    })
    vi.mocked(useMediaQuery).mockReturnValue(true)
  })

  // Verifies that Send button is disabled when draft is empty and enables upon typing content.
  it("enforces disabled send button when input is empty or whitespace only", () => {
    renderWithProviders(<ChatPanel />, { role: "patient" })

    const sendBtn = screen.getByRole("button", { name: "Send" })
    expect(sendBtn).toBeDisabled()

    const textarea = screen.getByRole("textbox", { name: "Message Gluco" })
    fireEvent.change(textarea, { target: { value: "   " } })
    expect(sendBtn).toBeDisabled()

    fireEvent.change(textarea, { target: { value: "Hello Gluco" } })
    expect(sendBtn).not.toBeDisabled()
  })

  // Verifies that pressing Enter key dispatches the message and clears the draft input.
  it("submits message and resets input when pressing Enter without shift", () => {
    renderWithProviders(<ChatPanel />, { role: "patient" })

    const textarea = screen.getByRole("textbox", { name: "Message Gluco" })
    fireEvent.change(textarea, {
      target: { value: "Why did my score change?" },
    })
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false })

    expect(mockSend).toHaveBeenCalledWith("Why did my score change?")
    expect(textarea).toHaveValue("")
  })

  // Verifies that pressing Shift+Enter does not trigger send and preserves newline formatting.
  it("allows multiline input without submitting when Shift+Enter is pressed", () => {
    renderWithProviders(<ChatPanel />, { role: "patient" })

    const textarea = screen.getByRole("textbox", { name: "Message Gluco" })
    fireEvent.change(textarea, { target: { value: "Line one" } })
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true })

    expect(mockSend).not.toHaveBeenCalled()
  })

  // Verifies that active streaming replaces Send with Stop button and invokes stop when clicked.
  it("replaces send button with stop button during streaming and invokes stop on click", () => {
    vi.mocked(useChat).mockReturnValue({
      ...baseChatState,
      streaming: true,
    } as unknown as ReturnType<typeof useChat>)

    renderWithProviders(<ChatPanel />, { role: "patient" })

    expect(
      screen.queryByRole("button", { name: "Send" })
    ).not.toBeInTheDocument()
    const stopBtn = screen.getByRole("button", { name: "Stop answering" })
    expect(stopBtn).toBeInTheDocument()

    fireEvent.click(stopBtn)
    expect(mockStop).toHaveBeenCalledTimes(1)
  })

  // Verifies that greeting and audience prompt suggestions render in empty conversation state.
  it("renders empty greeting and triggers send when prompt suggestion is clicked", () => {
    renderWithProviders(<ChatPanel />, { role: "patient" })

    expect(screen.getByText("Hi, I'm Gluco!")).toBeInTheDocument()
    expect(
      screen.getByText(
        "Ask me about your week, your score, or anything you're curious about."
      )
    ).toBeInTheDocument()

    const suggestionBtn = screen.getByRole("button", {
      name: "Why did my score change?",
    })
    fireEvent.click(suggestionBtn)

    expect(mockSend).toHaveBeenCalledWith("Why did my score change?")
  })

  // Verifies audience-specific titles and disclaimer text for patients and clinicians.
  it("renders audience-specific subtitles and disclaimers", () => {
    const { unmount } = renderWithProviders(<ChatPanel />, { role: "patient" })
    expect(screen.getByText("Your assistant")).toBeInTheDocument()
    expect(
      screen.getByText(/explains your data but can't diagnose/i)
    ).toBeInTheDocument()

    unmount()

    renderWithProviders(<ChatPanel />, { role: "clinician" })
    expect(screen.getByText("Clinical assistant")).toBeInTheDocument()
    expect(
      screen.getByText(/don't replace clinical judgment/i)
    ).toBeInTheDocument()
  })

  // Verifies that new conversation button is disabled when empty and triggers newChat when populated.
  it("controls new conversation button state based on message count and streaming", () => {
    const { rerender } = renderWithProviders(<ChatPanel />, { role: "patient" })
    const newChatBtn = screen.getByRole("button", { name: "New conversation" })
    expect(newChatBtn).toBeDisabled()

    vi.mocked(useChat).mockReturnValue({
      ...baseChatState,
      messages: [
        { id: "m1", role: "user", parts: [{ kind: "text", text: "Hi" }] },
      ],
    } as unknown as ReturnType<typeof useChat>)

    rerender(<ChatPanel />)
    expect(newChatBtn).not.toBeDisabled()

    fireEvent.click(newChatBtn)
    expect(mockNewChat).toHaveBeenCalledTimes(1)
  })

  // Verifies that close button invokes onClose callback when provided.
  it("invokes onClose callback when close button is clicked", () => {
    const mockClose = vi.fn()
    renderWithProviders(<ChatPanel onClose={mockClose} />, { role: "patient" })

    const closeBtn = screen.getByRole("button", { name: "Close chat" })
    fireEvent.click(closeBtn)

    expect(mockClose).toHaveBeenCalledTimes(1)
  })

  // Verifies that loadingThread indicator renders when switching conversations.
  it("displays loading thread marker when loadingThread is true", () => {
    vi.mocked(useChat).mockReturnValue({
      ...baseChatState,
      loadingThread: true,
    } as unknown as ReturnType<typeof useChat>)

    renderWithProviders(<ChatPanel />, { role: "patient" })

    expect(screen.getByText("Opening conversation…")).toBeInTheDocument()
  })

  it("offers a retry when conversation history fails to load", async () => {
    const api = fakeApi({
      "GET /catalog": { metrics: [] },
      "GET /widgets": [],
      "GET /chat/sessions": new Reply(403, { detail: "Unavailable" }),
    })

    renderWithProviders(<ChatPanel />, { role: "patient" })
    await userEvent.click(
      screen.getByRole("button", { name: "Past conversations" })
    )

    const retry = await screen.findByText("Couldn't load conversations. Retry")
    expect(screen.queryByText("No conversations yet")).not.toBeInTheDocument()
    await userEvent.click(retry)
    await waitFor(() =>
      expect(
        api.calls.filter((call) => call.path === "/chat/sessions").length
      ).toBeGreaterThan(1)
    )
  })

  // Verifies that floating launcher button renders with accessible label.
  it("renders floating launcher trigger with accessible name", () => {
    vi.mocked(useChat).mockReturnValue({
      streaming: false,
    } as unknown as ReturnType<typeof useChat>)
    vi.mocked(useMediaQuery).mockReturnValue(true)

    renderWithProviders(<ChatLauncher />, { role: "patient" })

    expect(
      screen.getByRole("button", { name: "Ask Gluco" })
    ).toBeInTheDocument()
  })

  // Verifies that clicking launcher opens the chat panel.
  it("opens the chat panel popover when launcher is clicked", () => {
    vi.mocked(useChat).mockReturnValue({
      sessionId: "s1",
      messages: [],
      streaming: false,
      loadingThread: false,
      send: vi.fn(),
      stop: vi.fn(),
      newChat: vi.fn(),
      openThread: vi.fn(),
    } as unknown as ReturnType<typeof useChat>)
    vi.mocked(useMediaQuery).mockReturnValue(true)

    renderWithProviders(<ChatLauncher />, { role: "patient" })

    const launcherBtn = screen.getByRole("button", { name: "Ask Gluco" })
    fireEvent.click(launcherBtn)

    expect(screen.getByText("Your assistant")).toBeInTheDocument()
  })
})
