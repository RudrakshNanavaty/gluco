import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { api, ApiError } from "@/lib/api/client"
import { LIVE } from "@/lib/api/queries"
import type { ClockState, TickEvent } from "@/lib/api/events"
import * as sseModule from "@/lib/api/sse"
import { ClockProvider, useClock } from "@/lib/clock"
import * as liveModule from "@/lib/live"

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
  },
}))

const MOCK_CLOCK: ClockState = {
  now: "2026-10-04T07:15:00Z",
  playing: true,
  seconds_per_hour: 5,
  enabled: true,
  data_start: "2026-09-27T05:00:00Z",
  data_end: "2026-10-04T07:00:00Z",
  at_end: false,
}

const MOCK_TICK: TickEvent = {
  type: "tick",
  clock: MOCK_CLOCK,
  reset: false,
  new_windows: [],
  live_at: "2026-10-04T07:15:00Z",
  live: [],
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ClockProvider>{children}</ClockProvider>
      </QueryClientProvider>
    )
  }
}

describe("useClock", () => {
  // Verifies error thrown when hook is used outside Provider context
  it("throws error when used outside ClockProvider", () => {
    expect(() => renderHook(() => useClock())).toThrow(
      "useClock must be used inside <ClockProvider>"
    )
  })
})

describe("ClockProvider", () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.restoreAllMocks()
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
  })

  // Verifies stream connection and state update when tick event arrives
  it("connects to stream and updates clock and connected state on tick", async () => {
    let capturedCallback: ((data: unknown, event: string) => void) | null = null

    vi.spyOn(sseModule, "streamSSE").mockImplementation(
      async (_path, _init, onEvent) => {
        capturedCallback = onEvent
        // Keep stream pending until aborted
        return new Promise(() => {})
      }
    )

    const wrapper = createWrapper(queryClient)
    const { result } = renderHook(() => useClock(), { wrapper })

    expect(result.current.connected).toBe(false)
    expect(result.current.clock).toBeNull()

    act(() => {
      capturedCallback?.(MOCK_TICK, "message")
    })

    expect(result.current.connected).toBe(true)
    expect(result.current.clock).toEqual(MOCK_CLOCK)
  })

  // Verifies live sensor metrics are published to live store on tick
  it("forwards tick live readings to publishLive", async () => {
    const publishSpy = vi.spyOn(liveModule, "publishLive")

    vi.spyOn(sseModule, "streamSSE").mockImplementation(
      async (_path, _init, onEvent) => {
        onEvent(MOCK_TICK, "message")
        return new Promise(() => {})
      }
    )

    const wrapper = createWrapper(queryClient)
    renderHook(() => useClock(), { wrapper })

    expect(publishSpy).toHaveBeenCalledWith(
      MOCK_TICK.live_at,
      MOCK_TICK.live
    )
  })

  // Verifies query invalidation on backwards seek reset
  it("invalidates all data queries when tick specifies reset", async () => {
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries")

    vi.spyOn(sseModule, "streamSSE").mockImplementation(
      async (_path, _init, onEvent) => {
        onEvent({ ...MOCK_TICK, reset: true }, "message")
        return new Promise(() => {})
      }
    )

    const wrapper = createWrapper(queryClient)
    renderHook(() => useClock(), { wrapper })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["data"],
      refetchType: "all",
    })
  })

  // Verifies incremental query invalidation when new analytics windows arrive
  it("invalidates data queries when tick has new windows without reset", async () => {
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries")

    vi.spyOn(sseModule, "streamSSE").mockImplementation(
      async (_path, _init, onEvent) => {
        onEvent({ ...MOCK_TICK, new_windows: ["win_1"] }, "message")
        return new Promise(() => {})
      }
    )

    const wrapper = createWrapper(queryClient)
    renderHook(() => useClock(), { wrapper })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["data"] })
  })

  // Verifies live-marked queries refresh when live readings change, at most every 5 s
  it("refreshes live queries on new live readings, at most every 5 s", () => {
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries")
    let emit: (tick: TickEvent) => void = () => {}
    vi.spyOn(sseModule, "streamSSE").mockImplementation(
      async (_path, _init, onEvent) => {
        emit = (tick) => onEvent(tick, "message")
        return new Promise(() => {})
      }
    )
    const now = vi.spyOn(Date, "now").mockReturnValue(10_000)

    renderHook(() => useClock(), { wrapper: createWrapper(queryClient) })
    act(() => emit({ ...MOCK_TICK, live_at: "2026-10-04T07:15:01Z" }))
    act(() => emit({ ...MOCK_TICK, live_at: "2026-10-04T07:15:02Z" }))
    now.mockReturnValue(15_000)
    act(() => emit({ ...MOCK_TICK, live_at: "2026-10-04T07:15:03Z" }))

    const live = invalidateSpy.mock.calls.filter(
      ([filters]) => filters?.predicate !== undefined
    )
    expect(live).toHaveLength(2)
    const predicate = live[0][0]!.predicate!
    expect(predicate({ meta: LIVE } as never)).toBe(true)
    expect(predicate({ meta: undefined } as never)).toBe(false)
  })

  // Verifies termination of stream reconnect loop on 401 unauthorized error
  it("stops reconnect attempts when stream returns 401 error", async () => {
    const streamSpy = vi
      .spyOn(sseModule, "streamSSE")
      .mockRejectedValue(new ApiError(401, "unauthorized", "Token expired"))

    const wrapper = createWrapper(queryClient)
    renderHook(() => useClock(), { wrapper })

    await waitFor(() => {
      expect(streamSpy).toHaveBeenCalledTimes(1)
    })
  })

  // Verifies control command execution and clock state update
  it("dispatches control commands and updates clock state with response", async () => {
    vi.spyOn(sseModule, "streamSSE").mockImplementation(() => new Promise(() => {}))

    const updatedClock = { ...MOCK_CLOCK, playing: false }
    const postSpy = vi.spyOn(api, "POST").mockResolvedValue({
      data: updatedClock,
      response: new Response(null, { status: 200 }),
    } as unknown as Awaited<ReturnType<typeof api.POST>>)

    const wrapper = createWrapper(queryClient)
    const { result } = renderHook(() => useClock(), { wrapper })

    await act(async () => {
      await result.current.control({ action: "pause" })
    })

    expect(postSpy).toHaveBeenCalledWith("/clock", { body: { action: "pause" } })
    expect(result.current.clock).toEqual(updatedClock)
  })

  // Verifies cleanup upon unmount aborts stream and resets live store
  it("cleans up stream connection and resets live store on unmount", () => {
    const publishSpy = vi.spyOn(liveModule, "publishLive")
    let capturedSignal: AbortSignal | undefined

    vi.spyOn(sseModule, "streamSSE").mockImplementation(
      async (_path, init) => {
        capturedSignal = init.signal
        return new Promise(() => {})
      }
    )

    const wrapper = createWrapper(queryClient)
    const { unmount } = renderHook(() => useClock(), { wrapper })

    expect(capturedSignal?.aborted).toBe(false)

    unmount()

    expect(capturedSignal?.aborted).toBe(true)
    expect(publishSpy).toHaveBeenCalledWith(null, [])
  })
})
