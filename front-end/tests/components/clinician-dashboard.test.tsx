import { act, fireEvent, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { CohortOverview } from "@/components/clinician/cohort-overview"
import { ParticipantDetail } from "@/components/clinician/participant-detail"
import { ParticipantTable } from "@/components/clinician/participant-table"
import { useLiveReading, useLiveReadings } from "@/lib/live"
import { fakeApi, PENDING, Reply } from "../fake-api"
import { mockRouter, renderWithProviders } from "../test-utils"

vi.mock("@/lib/live", () => ({
  useLiveReadings: vi.fn(),
  useLiveReading: vi.fn(),
}))

describe("Clinician Dashboard Components", () => {
  const sampleMetrics = [
    { name: "gluco_score", label: "Gluco Score", unit: "", live: false, description: "Composite score" },
    { name: "gluco_change_24h", label: "24 h Change", unit: "", live: false, description: "Change over 24 hours" },
    { name: "heart_rate", label: "Heart Rate", unit: "bpm", live: true, description: "Current pulse" },
    { name: "wrist_temp", label: "Wrist Temp", unit: "°C", live: false, description: "Skin temperature" },
  ]

  const catalog = { metrics: sampleMetrics }
  const serverError = new Reply(500, { detail: "Server failure" })

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useLiveReadings).mockReturnValue({
      timestamp: "2026-10-16T12:00:00Z",
      byPerson: new Map(),
    } as unknown as ReturnType<typeof useLiveReadings>)
    vi.mocked(useLiveReading).mockReturnValue(undefined)
  })

  describe("CohortOverview", () => {
    const sampleCohortData = {
      participants: 18,
      gluco_score: { median: 84, mean: 83.6, min: 61, max: 97 },
      lowest_gluco: [
        { person_id: "p-1", display_name: "Patient One", window_end: "2026-10-16T12:00:00Z", values: { gluco_score: 61, gluco_change_24h: -4.2 } },
      ],
      biggest_drops: [
        { person_id: "p-2", display_name: "Patient Two", window_end: "2026-10-16T12:00:00Z", values: { gluco_score: 72, gluco_change_24h: -11.5 } },
      ],
      biggest_gains: [
        { person_id: "p-3", display_name: "Patient Three", window_end: "2026-10-16T12:00:00Z", values: { gluco_score: 91, gluco_change_24h: 8.3 } },
      ],
    }

    // Verifies that skeleton placeholders render when cohort summary data is loading.
    it("renders skeletons while cohort query is pending", () => {
      fakeApi({ "GET /catalog": catalog, "GET /cohort": PENDING })

      const { container } = renderWithProviders(<CohortOverview />, { role: "clinician" })

      const skeletons = container.querySelectorAll("[data-slot=skeleton], .animate-pulse")
      expect(skeletons.length).toBeGreaterThan(0)
    })

    // Verifies that a destructive error banner renders when loading the cohort fails.
    it("renders destructive alert when cohort query fails", async () => {
      fakeApi({ "GET /catalog": catalog, "GET /cohort": serverError })

      renderWithProviders(<CohortOverview />, { role: "clinician" })

      expect(await screen.findByText("Couldn't load your patient panel")).toBeInTheDocument()
      expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument()
    })

    // Verifies that aggregate statistics and ranked participant sections render correctly on success.
    it("renders panel statistics and ranked patient lists on success", async () => {
      fakeApi({ "GET /catalog": catalog, "GET /cohort": sampleCohortData })

      renderWithProviders(<CohortOverview />, { role: "clinician" })

      expect(await screen.findByText("Patients")).toBeInTheDocument()
      expect(screen.getByText("18")).toBeInTheDocument()
      expect(screen.getByText("Median Gluco Score")).toBeInTheDocument()
      expect(screen.getByText("84")).toBeInTheDocument()
      expect(screen.getByText("Mean 84")).toBeInTheDocument()
      expect(screen.getAllByText("Lowest Gluco Score").length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText("Patient One")).toBeInTheDocument()
      expect(screen.getByText("Patient Two")).toBeInTheDocument()
      expect(screen.getByText("Patient Three")).toBeInTheDocument()
    })

    // Verifies that fallback text renders when ranked participant lists are empty.
    it("renders empty list placeholder when no patients exist in ranked lists", async () => {
      fakeApi({
        "GET /catalog": catalog,
        "GET /cohort": {
          participants: 0,
          gluco_score: { median: null, mean: null, min: null, max: null },
          lowest_gluco: [],
          biggest_drops: [],
          biggest_gains: [],
        },
      })

      renderWithProviders(<CohortOverview />, { role: "clinician" })

      const emptyPlaceholders = await screen.findAllByText("No patients to show yet.")
      expect(emptyPlaceholders.length).toBe(3)
    })

    // Verifies that an error message displays when the cohort trend query fails.
    it("renders error message when cohort trend query fails", async () => {
      fakeApi({
        "GET /catalog": catalog,
        "GET /cohort": sampleCohortData,
        "POST /query": serverError,
      })

      renderWithProviders(<CohortOverview />, { role: "clinician" })

      expect(await screen.findByText("Something went wrong. Please try again.")).toBeInTheDocument()
    })
  })

  describe("ParticipantTable", () => {
    const sampleParticipants = [
      {
        person_id: "pat-101",
        display_name: "John Miller",
        window_end: "2026-10-16T12:00:00Z",
        values: {
          gluco_score: 87,
          gluco_change_24h: 3.1,
          heart_rate: 68,
          wrist_temp: 33.8,
        },
      },
    ]

    // Verifies that table skeletons render when participants data is pending.
    it("renders skeleton rows when participants query is pending", () => {
      fakeApi({ "GET /catalog": catalog, "GET /participants": PENDING })

      const { container } = renderWithProviders(<ParticipantTable />, { role: "clinician" })

      const skeletons = container.querySelectorAll("[data-slot=skeleton], .animate-pulse")
      expect(skeletons.length).toBeGreaterThan(0)
    })

    // Verifies that a destructive alert renders when loading participants fails.
    it("renders destructive alert when participants query fails", async () => {
      fakeApi({ "GET /catalog": catalog, "GET /participants": serverError })

      renderWithProviders(<ParticipantTable />, { role: "clinician" })

      expect(await screen.findByText("Something went wrong. Please try again.")).toBeInTheDocument()
    })

    // Verifies that table headers and participant rows render correctly on success.
    it("renders table columns, participant rows, and formatted values", async () => {
      fakeApi({ "GET /catalog": catalog, "GET /participants": sampleParticipants })

      renderWithProviders(<ParticipantTable />, { role: "clinician" })

      expect(await screen.findByText("John Miller")).toBeInTheDocument()
      expect(screen.getByText("87")).toBeInTheDocument()
      expect(screen.getByText("+3.1")).toBeInTheDocument()
      expect(screen.getByText("68.0")).toBeInTheDocument()
      expect(screen.getByText("33.8")).toBeInTheDocument()
    })

    // Verifies that live sensor readings override the 24h summary values for live metric columns.
    it("displays live sensor readings from useLiveReadings in the live metric cell", async () => {
      fakeApi({ "GET /catalog": catalog, "GET /participants": sampleParticipants })
      vi.mocked(useLiveReadings).mockReturnValue({
        timestamp: "2026-10-16T12:00:01Z",
        byPerson: new Map([
          ["pat-101", { person_id: "pat-101", sensor_time: "2026-10-16T12:00:01Z", values: { heart_rate: 95 } }],
        ]),
      } as unknown as ReturnType<typeof useLiveReadings>)

      renderWithProviders(<ParticipantTable />, { role: "clinician" })

      expect(await screen.findByText("95.0")).toBeInTheDocument()
    })

    // Verifies that clicking a column header toggles the sort order and updates aria-sort attribute.
    it("toggles sorting order and asks the server for the new order", async () => {
      const api = fakeApi({ "GET /catalog": catalog, "GET /participants": sampleParticipants })

      renderWithProviders(<ParticipantTable />, { role: "clinician" })

      const glucoScoreBtn = await screen.findByRole("button", { name: /gluco score/i })
      const tableHead = glucoScoreBtn.closest("th")
      expect(tableHead).toHaveAttribute("aria-sort", "ascending")

      act(() => {
        fireEvent.click(glucoScoreBtn)
      })

      expect(tableHead).toHaveAttribute("aria-sort", "descending")
      await waitFor(() =>
        expect(
          api.calls
            .filter((c) => c.path === "/participants")
            .map((c) => c.query.get("order"))
        ).toEqual(["asc", "desc"])
      )
    })

    // Verifies that clicking a table row navigates to the participant detail page.
    it("navigates to participant detail route when clicking a row", async () => {
      fakeApi({ "GET /catalog": catalog, "GET /participants": sampleParticipants })

      renderWithProviders(<ParticipantTable />, { role: "clinician" })

      const row = (await screen.findByText("John Miller")).closest("tr")
      expect(row).toBeInTheDocument()

      act(() => {
        fireEvent.click(row!)
      })

      expect(mockRouter.push).toHaveBeenCalledWith("/clinician/participants/pat-101")
    })
  })

  describe("ParticipantDetail", () => {
    const sampleParticipant = {
      person_id: "pat-200",
      display_name: "Sarah Connor",
      window_end: "2026-10-16T12:00:00Z",
      values: {
        gluco_score: 94,
        gluco_change_24h: 1.5,
      },
    }

    // Verifies that skeleton placeholders render when participant detail data is pending.
    it("renders loading skeletons while participant query is pending", () => {
      fakeApi({ "GET /catalog": catalog, "GET /participants/{person_id}": PENDING })

      const { container } = renderWithProviders(<ParticipantDetail id="pat-200" />, { role: "clinician" })

      const skeletons = container.querySelectorAll("[data-slot=skeleton], .animate-pulse")
      expect(skeletons.length).toBeGreaterThan(0)
    })

    // Verifies that an empty state with back navigation displays when patient is not found.
    it("renders patient not found empty state when participant query fails", async () => {
      fakeApi({
        "GET /catalog": catalog,
        "GET /participants/{person_id}": new Reply(404, {
          detail: "Patient not found",
          code: "not_found",
        }),
      })

      renderWithProviders(<ParticipantDetail id="pat-200" />, { role: "clinician" })

      expect(await screen.findByText("Patient not found")).toBeInTheDocument()
      expect(screen.getByRole("link", { name: /back to patient panel/i })).toHaveAttribute("href", "/clinician")
    })

    // Verifies that patient name, window time, GlucoScore, and back button render on success.
    it("renders participant header, window end, and GlucoScore on success", async () => {
      fakeApi({
        "GET /catalog": catalog,
        "GET /participants/{person_id}": ({ params }) =>
          params.person_id === "pat-200" ? sampleParticipant : new Reply(404, {}),
      })

      renderWithProviders(<ParticipantDetail id="pat-200" />, { role: "clinician" })

      expect(await screen.findByText("Sarah Connor")).toBeInTheDocument()
      expect(screen.getByText(/latest 24 h window ends/i)).toBeInTheDocument()
      expect(screen.getByRole("link", { name: /all patients/i })).toHaveAttribute("href", "/clinician")
    })

    // Verifies that live sensor card renders when live readings are present.
    it("renders live sensors card when live readings are present", async () => {
      fakeApi({
        "GET /catalog": catalog,
        "GET /participants/{person_id}": ({ params }) =>
          params.person_id === "pat-200" ? sampleParticipant : new Reply(404, {}),
      })
      vi.mocked(useLiveReading).mockReturnValue({
        person_id: "pat-200",
        sensor_time: "2026-10-16T12:00:00Z",
        values: { heart_rate: 76 },
      } as unknown as ReturnType<typeof useLiveReading>)

      renderWithProviders(<ParticipantDetail id="pat-200" />, { role: "clinician" })

      expect(await screen.findByText("Live sensors")).toBeInTheDocument()
      expect(screen.getByText(/updated every second/i)).toBeInTheDocument()
    })

    // Verifies that toggling the time range updates the selected range in the toggle group.
    it("allows toggling time range between 24 h, 72 h, and 7 d", async () => {
      fakeApi({
        "GET /catalog": catalog,
        "GET /participants/{person_id}": ({ params }) =>
          params.person_id === "pat-200" ? sampleParticipant : new Reply(404, {}),
      })

      renderWithProviders(<ParticipantDetail id="pat-200" />, { role: "clinician" })

      const timeRangeGroup = await screen.findByRole("radiogroup", { name: "Time range" })
      const toggle24h = within(timeRangeGroup).getByRole("radio", { name: "24 h" })
      expect(toggle24h).toHaveAttribute("aria-checked", "false")

      act(() => {
        fireEvent.click(toggle24h)
      })

      expect(toggle24h).toHaveAttribute("aria-checked", "true")
    })
  })
})
