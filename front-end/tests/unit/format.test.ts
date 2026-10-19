import { afterEach, describe, expect, it, vi } from "vitest"

import {
  formatClockTime,
  formatReplayDay,
  formatReplayTime,
  formatTick,
  ordinal,
} from "@/lib/format"

describe("formatReplayTime", () => {
  // Verifies standard UTC conversion to "Weekday Day Month, HH:MM"
  it("formats valid ISO timestamp to UTC replay time", () => {
    expect(formatReplayTime("2026-10-04T07:15:00Z")).toBe("Sun 4 Oct, 07:15")
  })

  // Verifies leap year date handling in UTC
  it("formats leap day timestamp accurately", () => {
    expect(formatReplayTime("2024-02-29T23:59:00Z")).toBe("Thu 29 Feb, 23:59")
  })

  // Verifies fallback placeholder when timestamp is null, undefined, or empty
  it("returns fallback dash for missing values", () => {
    expect(formatReplayTime(null)).toBe("—")
    expect(formatReplayTime(undefined)).toBe("—")
    expect(formatReplayTime("")).toBe("—")
  })

  // Verifies unhandled exception when date string is not parseable by Intl formatter
  it("throws RangeError when timestamp is invalid", () => {
    expect(() => formatReplayTime("invalid-timestamp")).toThrow(RangeError)
  })
})

describe("formatClockTime", () => {
  // Verifies conversion of ISO timestamp to live clock format "HH:MM:SS"
  it("formats ISO timestamp with two-digit seconds", () => {
    expect(formatClockTime("2026-10-04T14:07:12Z")).toBe("14:07:12")
  })

  // Verifies single-digit seconds are zero-padded
  it("pads single-digit seconds with leading zero", () => {
    expect(formatClockTime("2026-10-04T09:05:03Z")).toBe("09:05:03")
  })

  // Verifies handling of timestamps with millisecond fractions
  it("formats timestamps with milliseconds accurately", () => {
    expect(formatClockTime("2026-10-04T14:07:12.850Z")).toBe("14:07:12")
  })

  // Verifies fallback placeholder when timestamp is missing
  it("returns fallback dash for missing values", () => {
    expect(formatClockTime(null)).toBe("—")
    expect(formatClockTime(undefined)).toBe("—")
    expect(formatClockTime("")).toBe("—")
  })

  // Verifies unhandled exception when date string is invalid
  it("throws RangeError when timestamp is invalid", () => {
    expect(() => formatClockTime("not-a-valid-date")).toThrow(RangeError)
  })
})

describe("formatReplayDay", () => {
  // Verifies date-only formatting omitting time components
  it("formats ISO timestamp to day without time", () => {
    expect(formatReplayDay("2026-10-04T07:00:00Z")).toBe("Sun 4 Oct")
  })

  // Verifies year boundary transitions in UTC
  it("formats year-end and year-start timestamps accurately", () => {
    expect(formatReplayDay("2026-12-31T23:59:59Z")).toBe("Thu 31 Dec")
    expect(formatReplayDay("2027-01-01T00:00:01Z")).toBe("Fri 1 Jan")
  })

  // Verifies fallback placeholder when timestamp is missing
  it("returns fallback dash for missing values", () => {
    expect(formatReplayDay(null)).toBe("—")
    expect(formatReplayDay(undefined)).toBe("—")
    expect(formatReplayDay("")).toBe("—")
  })

  // Verifies unhandled exception when date string is invalid
  it("throws RangeError when timestamp is invalid", () => {
    expect(() => formatReplayDay("bad-date")).toThrow(RangeError)
  })
})

describe("formatTick", () => {
  // Verifies axis tick format for day-bucketed queries
  it("formats tick for day bucket", () => {
    expect(formatTick("2026-10-04T07:00:00Z", "day")).toBe("Sun 4")
  })

  // Verifies axis tick format for sub-day (hour) queries
  it("formats tick for non-day bucket", () => {
    expect(formatTick("2026-10-04T07:00:00Z", "hour")).toBe("Sun 07:00")
  })

  // Verifies unhandled exception when timestamp is invalid
  it("throws RangeError when timestamp is invalid", () => {
    expect(() => formatTick("unparseable-date", "day")).toThrow(RangeError)
  })
})

describe("ordinal", () => {
  // Verifies special English teen suffix handling (11th, 12th, 13th)
  it("applies th suffix to teen numbers", () => {
    expect(ordinal(11)).toBe("11th")
    expect(ordinal(12)).toBe("12th")
    expect(ordinal(13)).toBe("13th")
  })

  // Verifies teen suffix handling for numbers above 100 ending in 11, 12, or 13
  it("applies th suffix to centennial teen numbers", () => {
    expect(ordinal(111)).toBe("111th")
    expect(ordinal(112)).toBe("112th")
    expect(ordinal(213)).toBe("213th")
  })

  // Verifies standard st, nd, and rd suffixes
  it("applies st, nd, and rd suffixes to terminal 1, 2, and 3", () => {
    expect(ordinal(1)).toBe("1st")
    expect(ordinal(2)).toBe("2nd")
    expect(ordinal(3)).toBe("3rd")
    expect(ordinal(21)).toBe("21st")
    expect(ordinal(32)).toBe("32nd")
    expect(ordinal(43)).toBe("43rd")
  })

  // Verifies generic th suffix for numbers ending in 4 through 0
  it("applies th suffix to standard terminal digits", () => {
    expect(ordinal(0)).toBe("0th")
    expect(ordinal(4)).toBe("4th")
    expect(ordinal(10)).toBe("10th")
    expect(ordinal(20)).toBe("20th")
    expect(ordinal(100)).toBe("100th")
  })

  // Verifies mathematical rounding for floating-point inputs
  it("rounds floating-point inputs to nearest integer", () => {
    expect(ordinal(1.2)).toBe("1st")
    expect(ordinal(20.8)).toBe("21st")
    expect(ordinal(11.4)).toBe("11th")
  })

  // Verifies negative integer behavior
  it("defaults to th suffix for negative numbers", () => {
    expect(ordinal(-1)).toBe("-1th")
    expect(ordinal(-11)).toBe("-11th")
  })
})

describe("local timezone", () => {
  // The formatters read the default timezone when the module loads, so load a
  // fresh copy per zone.
  async function inZone(zone: string) {
    const previous = process.env.TZ
    process.env.TZ = zone
    vi.resetModules()
    const format = await import("@/lib/format")
    process.env.TZ = previous
    return format
  }

  afterEach(() => {
    vi.resetModules()
  })

  // Verifies times of day follow the viewer's zone (EDT is UTC-4 in October)
  it("shifts times of day into the local zone", async () => {
    const f = await inZone("America/New_York")
    expect(f.formatReplayTime("2026-10-04T07:15:00Z")).toBe("Sun 4 Oct, 03:15")
    expect(f.formatClockTime("2026-10-04T14:07:12Z")).toBe("10:07:12")
    expect(f.formatTick("2026-10-04T07:00:00Z", "hour")).toBe("Sun 03:00")
  })

  // Verifies the date rolls back when the local time is before midnight UTC
  it("rolls the local date back across midnight", async () => {
    const f = await inZone("America/New_York")
    expect(f.formatReplayTime("2026-10-04T02:30:00Z")).toBe("Sat 3 Oct, 22:30")
  })

  // Verifies seconds follow the local clock in zones with a fractional offset
  it("keeps seconds right in a half-hour zone", async () => {
    const f = await inZone("Asia/Kolkata")
    expect(f.formatClockTime("2026-10-04T14:07:12Z")).toBe("19:37:12")
  })

  // Verifies day labels stay on UTC days, matching the back-end's day buckets
  it("keeps day labels and day ticks in UTC", async () => {
    const f = await inZone("America/New_York")
    expect(f.formatReplayDay("2026-10-04T02:30:00Z")).toBe("Sun 4 Oct")
    expect(f.formatTick("2026-10-04T02:30:00Z", "day")).toBe("Sun 4")
  })
})
