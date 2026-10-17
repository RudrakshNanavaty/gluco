import { screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { PatientDashboard } from "@/components/patient/patient-dashboard"
import { ApiError } from "@/lib/api/client"
import {
  useCatalog,
  useExplain,
  useParticipant,
  usePinnedWidgets,
  useSeries,
} from "@/lib/api/queries"
import { useClock } from "@/lib/clock"
import { useLiveReading } from "@/lib/live"
import type { Principal } from "@/lib/session"
import { renderWithProviders } from "../test-utils"

vi.mock("@/lib/clock", () => ({
  useClock: vi.fn(),
}))

vi.mock("@/lib/live", () => ({
  useLiveReading: vi.fn(),
}))

vi.mock("@/lib/api/queries", () => ({
  keys: {
    participant: (id: string) => ["data", "participant", id],
    explain: (id: string, hours: number) => ["data", "explain", id, hours],
    query: (spec: unknown) => ["data", "query", spec],
    pins: ["pins"],
    widget: (id: string) => ["data", "widget", id],
    catalog: ["catalog"],
  },
  useParticipant: vi.fn(),
  useExplain: vi.fn(),
  useSeries: vi.fn(),
  useCatalog: vi.fn(),
  usePinnedWidgets: vi.fn(),
  useWidgetData: vi.fn(),
  useUnpinWidget: vi.fn(),
}))

describe("PatientDashboard", () => {
  const patientPrincipal: Principal = {
    user_id: "user-alice",
    role: "patient",
    display_name: "Alice Parker",
    participant_id: "pat-100",
  }

  const sampleCatalogMetrics = [
    { name: "gluco_score", label: "Gluco Score", unit: "", live: false, description: "Composite score" },
    { name: "gluco_change_24h", label: "24 h Change", unit: "", live: false, description: "24 h change" },
    { name: "hr_mean_bpm_24h", label: "Heart Rate", unit: "bpm", live: false, description: "24 h mean heart rate" },
    { name: "latest_hr_bpm", label: "Heart Rate now", unit: "bpm", live: true, description: "Current pulse" },
    { name: "motion_mean_g", label: "Movement", unit: "g", live: false, description: "24 h motion acceleration" },
    { name: "latest_motion_g", label: "Movement now", unit: "g", live: true, description: "Current motion" },
    { name: "temperature_mean_c_24h", label: "Skin Temperature", unit: "°C", live: false, description: "Skin temp" },
    { name: "latest_skin_temperature_c", label: "Skin Temp now", unit: "°C", live: true, description: "Current skin temp" },
    { name: "cadence_rpm", label: "Cadence", unit: "rpm", live: false, description: "Step cadence" },
  ]

  const sampleParticipantData = {
    person_id: "pat-100",
    display_name: "Alice Parker",
    window_end: "2026-10-16T12:00:00Z",
    values: {
      gluco_score: 85,
      gluco_change_24h: 3.2,
      hr_mean_bpm_24h: 72,
      motion_mean_g: 0.15,
      temperature_mean_c_24h: 34.2,
      cadence_rpm: 60,
    },
  }

  const sampleExplainData = {
    hours: 24,
    change: {
      baseline_window_hours: 168,
      changes: [
        {
          metric: "hr_mean_bpm_24h",
          baseline_mean: 70,
          current_mean: 72,
          z_vs_baseline: 0.5,
          percent_change: 2.8,
        },
        {
          metric: "motion_mean_g",
          baseline_mean: 0.12,
          current_mean: 0.15,
          z_vs_baseline: 1.2,
          percent_change: 25.0,
        },
        {
          metric: "temperature_mean_c_24h",
          baseline_mean: 34.0,
          current_mean: 34.2,
          z_vs_baseline: -0.2,
          percent_change: 0.5,
        },
      ],
    },
    drivers: [],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useClock).mockReturnValue({
      connected: true,
      clock: {
        now: "2026-10-16T12:00:00Z",
        playing: true,
        seconds_per_hour: 5,
        enabled: true,
        data_start: "2026-10-09T12:00:00Z",
        data_end: "2026-10-16T12:00:00Z",
        at_end: false,
      },
      control: vi.fn(),
    } as unknown as ReturnType<typeof useClock>)
    vi.mocked(useCatalog).mockReturnValue({
      data: { metrics: sampleCatalogMetrics },
      isSuccess: true,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useCatalog>)
    vi.mocked(useParticipant).mockReturnValue({
      data: sampleParticipantData,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useParticipant>)
    vi.mocked(useLiveReading).mockReturnValue(undefined)
    vi.mocked(useExplain).mockReturnValue({
      data: sampleExplainData,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useExplain>)
    vi.mocked(useSeries).mockReturnValue({
      data: undefined,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useSeries>)
    vi.mocked(usePinnedWidgets).mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof usePinnedWidgets>)
  })

  // Verifies that the greeting displays the user name and formatted clock replay timestamp.
  it("renders personalized greeting and formatted clock timestamp", () => {
    renderWithProviders(<PatientDashboard principal={patientPrincipal} />)

    expect(screen.getByRole("heading", { level: 1, name: "Hi, Alice Parker" })).toBeInTheDocument()
    expect(screen.getByText(/here's how your week looks, as of/i)).toBeInTheDocument()
    expect(screen.getByText(/Fri 16 Oct, 12:00/i)).toBeInTheDocument()
  })

  // Verifies that the Gluco Score section renders the score ring and plain-language trend explanation.
  it("renders Gluco Score ring and friendly change summary", () => {
    renderWithProviders(<PatientDashboard principal={patientPrincipal} />)

    expect(screen.getByRole("heading", { name: "Your Gluco Score" })).toBeInTheDocument()
    expect(screen.getByRole("meter", { name: "Gluco Score" })).toHaveAttribute("aria-valuenow", "85")
    expect(screen.getByText("Up 3 points since this time yesterday.")).toBeInTheDocument()
    expect(screen.getByText("Higher is healthier.")).toBeInTheDocument()
  })

  // Verifies that primary vital sensor cards render with values and baseline comparisons.
  it("renders primary vitals tiles for heart rate, movement, and skin temperature", () => {
    renderWithProviders(<PatientDashboard principal={patientPrincipal} />)

    expect(screen.getByRole("heading", { name: "Your vitals" })).toBeInTheDocument()
    expect(screen.getByText("Heart rate")).toBeInTheDocument()
    expect(screen.getByText("Movement")).toBeInTheDocument()
    expect(screen.getByText("Skin temperature")).toBeInTheDocument()
    expect(screen.getAllByText("Close to your usual").length).toBeGreaterThanOrEqual(1)
  })

  // Verifies that live sensor values display inside vital cards when live readings are present.
  it("displays live sensor readings within vital tiles when live readings exist", () => {
    vi.mocked(useLiveReading).mockReturnValue({
      person_id: "pat-100",
      sensor_time: "2026-10-16T12:00:01Z",
      values: {
        latest_hr_bpm: 88,
        latest_motion_g: 0.22,
        latest_skin_temperature_c: 34.5,
      },
    } as unknown as ReturnType<typeof useLiveReading>)

    renderWithProviders(<PatientDashboard principal={patientPrincipal} />)

    expect(screen.getAllByText("24-hour average").length).toBe(3)
    expect(screen.getByText("88.0")).toBeInTheDocument()
  })

  // Verifies that secondary sensor metrics render in the More from your wearable section.
  it("renders secondary sensor metrics in More from your wearable section", () => {
    renderWithProviders(<PatientDashboard principal={patientPrincipal} />)

    expect(screen.getByRole("heading", { name: "More from your wearable" })).toBeInTheDocument()
    expect(screen.getByText("Cadence")).toBeInTheDocument()
    expect(screen.getByText("60.0")).toBeInTheDocument()
  })

  // Verifies that a destructive error alert renders when participant data cannot be loaded.
  it("renders destructive alert banner when loading participant data fails", () => {
    vi.mocked(useParticipant).mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: new ApiError(500, undefined, "Participant service unavailable"),
    } as unknown as ReturnType<typeof useParticipant>)

    renderWithProviders(<PatientDashboard principal={patientPrincipal} />)

    expect(screen.getByText("We couldn't load your readings")).toBeInTheDocument()
    expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument()
  })

  // Verifies that skeleton placeholders render when participant data is still pending.
  it("renders skeleton placeholders while data queries are pending", () => {
    vi.mocked(useParticipant).mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as unknown as ReturnType<typeof useParticipant>)

    const { container } = renderWithProviders(<PatientDashboard principal={patientPrincipal} />)

    const skeletons = container.querySelectorAll("[data-slot=skeleton], .animate-pulse")
    expect(skeletons.length).toBeGreaterThan(0)
    expect(screen.queryByRole("meter", { name: "Gluco Score" })).not.toBeInTheDocument()
  })

  // Verifies that greeting omits the clock timestamp when clock.now is missing.
  it("omits timestamp gracefully when clock now is null", () => {
    vi.mocked(useClock).mockReturnValue({
      connected: true,
      clock: null,
      control: vi.fn(),
    } as unknown as ReturnType<typeof useClock>)

    renderWithProviders(<PatientDashboard principal={patientPrincipal} />)

    expect(screen.getByText("Here's how your week looks.")).toBeInTheDocument()
  })

  // Verifies that empty participant_id is handled safely without throwing runtime errors.
  it("handles missing participant_id on principal gracefully", () => {
    const anonymousPrincipal: Principal = {
      user_id: "anon",
      role: "patient",
      display_name: "Guest",
      participant_id: null,
    }

    renderWithProviders(<PatientDashboard principal={anonymousPrincipal} />)

    expect(screen.getByRole("heading", { level: 1, name: "Hi, Guest" })).toBeInTheDocument()
  })
})
