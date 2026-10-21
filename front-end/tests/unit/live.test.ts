import { act, renderHook } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"

import type { LiveReading } from "@/lib/api/events"
import { publishLive, useLiveReading, useLiveReadings } from "@/lib/live"

const READING_1: LiveReading = {
  person_id: "001",
  sensor_time: "2026-10-04T07:15:00Z",
  analytics_window_end: "2026-10-04T07:00:00Z",
  values: {
    hr_bpm_1s: 72,
    motion_g_1s: 0.05,
    temp_c_1s: 33.5,
  },
}

const READING_2: LiveReading = {
  person_id: "002",
  sensor_time: "2026-10-04T07:15:00Z",
  analytics_window_end: "2026-10-04T07:00:00Z",
  values: {
    hr_bpm_1s: 85,
    motion_g_1s: 0.12,
    temp_c_1s: 34.1,
  },
}

describe("publishLive", () => {
  beforeEach(() => {
    publishLive(null, [])
  })

  // Verifies store updates timestamp and indexes readings by participant ID
  it("updates snapshot timestamp and populates participant map", () => {
    const { result } = renderHook(() => useLiveReadings())

    act(() => {
      publishLive("2026-10-04T07:15:00Z", [READING_1, READING_2])
    })

    expect(result.current.at).toBe("2026-10-04T07:15:00Z")
    expect(result.current.byPerson.size).toBe(2)
    expect(result.current.byPerson.get("001")).toEqual(READING_1)
    expect(result.current.byPerson.get("002")).toEqual(READING_2)
  })

  // Verifies duplicate suppression optimization when timestamp and length are identical
  it("avoids redundant updates when timestamp and reading count match", () => {
    act(() => {
      publishLive("2026-10-04T07:15:00Z", [READING_1])
    })

    const { result } = renderHook(() => useLiveReadings())
    const initialMap = result.current.byPerson

    const modifiedReading = { ...READING_1, values: { hr_bpm_1s: 99 } }

    act(() => {
      // Same timestamp and same array length: should be ignored by optimization guard
      publishLive("2026-10-04T07:15:00Z", [modifiedReading])
    })

    expect(result.current.byPerson).toBe(initialMap)
    expect(result.current.byPerson.get("001")?.values.hr_bpm_1s).toBe(72)
  })

  // Verifies reset to empty state when null and empty array are passed
  it("clears active snapshot to empty state", () => {
    act(() => {
      publishLive("2026-10-04T07:15:00Z", [READING_1])
    })

    const { result } = renderHook(() => useLiveReadings())
    expect(result.current.at).not.toBeNull()

    act(() => {
      publishLive(null, [])
    })

    expect(result.current.at).toBeNull()
    expect(result.current.byPerson.size).toBe(0)
  })
})

describe("useLiveReading", () => {
  beforeEach(() => {
    publishLive(null, [])
  })

  // Verifies retrieval of specific participant reading
  it("returns reading for existing participant ID", () => {
    act(() => {
      publishLive("2026-10-04T07:15:00Z", [READING_1, READING_2])
    })

    const { result } = renderHook(() => useLiveReading("001"))
    expect(result.current).toEqual(READING_1)
  })

  // Verifies undefined return for missing, null, or undefined participant IDs
  it("returns undefined when participant ID is missing or not in store", () => {
    act(() => {
      publishLive("2026-10-04T07:15:00Z", [READING_1])
    })

    const { result: nullResult } = renderHook(() => useLiveReading(null))
    expect(nullResult.current).toBeUndefined()

    const { result: undefinedResult } = renderHook(() =>
      useLiveReading(undefined)
    )
    expect(undefinedResult.current).toBeUndefined()

    const { result: unknownResult } = renderHook(() =>
      useLiveReading("unknown_999")
    )
    expect(unknownResult.current).toBeUndefined()
  })

  // Verifies reactive update when participant readings change
  it("re-renders when targeted participant reading updates", () => {
    const { result } = renderHook(() => useLiveReading("001"))
    expect(result.current).toBeUndefined()

    act(() => {
      publishLive("2026-10-04T07:15:00Z", [READING_1])
    })

    expect(result.current).toEqual(READING_1)

    const updatedReading: LiveReading = {
      ...READING_1,
      sensor_time: "2026-10-04T07:15:01Z",
      values: { ...READING_1.values, hr_bpm_1s: 75 },
    }

    act(() => {
      publishLive("2026-10-04T07:15:01Z", [updatedReading])
    })

    expect(result.current?.values.hr_bpm_1s).toBe(75)
  })
})
