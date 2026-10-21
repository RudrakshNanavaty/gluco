import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError, OFFLINE_MESSAGE, setTokenSource } from "@/lib/api/client"
import { streamSSE } from "@/lib/api/sse"

function createSSEStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    },
  })
}

describe("streamSSE", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    setTokenSource(null)
  })

  // Verifies successful connection, header injection, and event decoding
  it("connects with stream headers and dispatches parsed JSON events", async () => {
    setTokenSource({ token: async () => "sse-token-123", rejected: vi.fn() })

    const stream = createSSEStream([
      'event: tick\ndata: {"type":"tick","count":1}\n\n',
      'event: custom\ndata: {"status":"active"}\n\n',
    ])

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      })
    )

    const events: Array<{ data: unknown; event: string }> = []
    const controller = new AbortController()

    await streamSSE("/stream", { signal: controller.signal }, (data, event) => {
      events.push({ data, event })
    })

    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const requestHeaders = new Headers(fetchSpy.mock.calls[0][1]?.headers)
    expect(requestHeaders.get("Accept")).toBe("text/event-stream")
    expect(requestHeaders.get("Authorization")).toBe("Bearer sse-token-123")

    expect(events).toEqual([
      { data: { type: "tick", count: 1 }, event: "tick" },
      { data: { status: "active" }, event: "custom" },
    ])
  })

  // Verifies fallback event name when the SSE event field is omitted
  it("defaults event name to message when event field is omitted", async () => {
    const stream = createSSEStream(['data: {"hello":"world"}\n\n'])
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      })
    )

    const events: Array<{ data: unknown; event: string }> = []
    await streamSSE(
      "/stream",
      { signal: new AbortController().signal },
      (data, event) => {
        events.push({ data, event })
      }
    )

    expect(events).toEqual([{ data: { hello: "world" }, event: "message" }])
  })

  // Verifies malformed non-JSON lines are skipped without halting stream consumption
  it("skips corrupted non-JSON data chunks and continues processing", async () => {
    const stream = createSSEStream([
      "event: tick\ndata: not-json\n\n",
      'event: tick\ndata: {"valid":true}\n\n',
    ])
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      })
    )

    const events: Array<{ data: unknown; event: string }> = []
    await streamSSE(
      "/stream",
      { signal: new AbortController().signal },
      (data, event) => {
        events.push({ data, event })
      }
    )

    expect(events).toEqual([{ data: { valid: true }, event: "tick" }])
  })

  // Verifies translation of network fetch rejections into status 0 ApiError
  it("throws ApiError status 0 when network connection fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("Network offline")
    )

    const call = streamSSE(
      "/stream",
      { signal: new AbortController().signal },
      vi.fn()
    )

    await expect(call).rejects.toMatchObject({
      status: 0,
      message: OFFLINE_MESSAGE,
    })
  })

  // Verifies abort signal rethrows the raw abort error rather than converting to ApiError
  it("rethrows raw abort cause when signal is aborted", async () => {
    const controller = new AbortController()
    controller.abort(
      new DOMException("The operation was aborted", "AbortError")
    )

    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new DOMException("The operation was aborted", "AbortError")
    )

    const call = streamSSE("/stream", { signal: controller.signal }, vi.fn())

    await expect(call).rejects.toThrow("The operation was aborted")
  })

  // Verifies a refused session ends after one retry and the stream throws ApiError
  it("handles 401 responses by ending the session and throwing ApiError", async () => {
    const rejected = vi.fn()
    setTokenSource({ token: async () => "expired-token", rejected })

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Token invalid", code: "not_permitted" }),
        {
          status: 401,
        }
      )
    )

    const call = streamSSE(
      "/stream",
      { signal: new AbortController().signal },
      vi.fn()
    )

    await expect(call).rejects.toMatchObject({
      status: 401,
      code: "not_permitted",
      message: "Token invalid",
    })
    expect(rejected).toHaveBeenCalledTimes(1)
  })

  // Verifies rejection when response body is null
  it("throws ApiError when response has no body", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 200 })
    )

    const call = streamSSE(
      "/stream",
      { signal: new AbortController().signal },
      vi.fn()
    )

    await expect(call).rejects.toBeInstanceOf(ApiError)
  })
})
