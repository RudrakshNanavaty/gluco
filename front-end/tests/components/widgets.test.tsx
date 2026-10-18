import { fireEvent, render, screen } from "@testing-library/react"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  ChangeBadge,
  friendlyChange,
  GlucoScore,
  ScoreRing,
} from "@/components/gluco-score"
import { PinnedWidgets } from "@/components/widgets/pinned-widgets"
import { WidgetView } from "@/components/widgets/widget-view"
import { ApiError } from "@/lib/api/client"
import type { QueryResult } from "@/lib/api/events"
import {
  useCatalog,
  usePinnedWidgets,
  useUnpinWidget,
  useWidgetData,
} from "@/lib/api/queries"
import { renderWithProviders } from "../test-utils"

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
  },
}))

vi.mock("@/lib/api/queries", () => ({
  keys: {
    pins: ["pins"],
    widget: (id: string) => ["data", "widget", id],
    catalog: ["catalog"],
  },
  usePinnedWidgets: vi.fn(),
  useWidgetData: vi.fn(),
  useUnpinWidget: vi.fn(),
  useCatalog: vi.fn(),
}))

describe("Score Visualizations and Widgets", () => {
  const sampleMetrics = [
    { name: "gluco_score", label: "Gluco Score", unit: "", live: false, description: "Composite score" },
    { name: "heart_rate", label: "Heart Rate", unit: "bpm", live: true, description: "Heart rate" },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useCatalog).mockReturnValue({
      data: { metrics: sampleMetrics },
      isSuccess: true,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useCatalog>)
  })

  describe("ScoreRing & GlucoScore", () => {
    // Verifies that ScoreRing renders valid score with proper accessibility attributes.
    it("renders score ring with value and accessible meter role", () => {
      render(<ScoreRing value={94} />)

      const meter = screen.getByRole("meter", { name: "Gluco Score" })
      expect(meter).toHaveAttribute("aria-valuenow", "94")
      expect(meter).toHaveAttribute("aria-valuetext", "94 out of 100")
      expect(screen.getByText("94")).toBeInTheDocument()
      expect(screen.getByText("of 100")).toBeInTheDocument()
    })

    // Verifies that ScoreRing displays fallback dash when score value is null or undefined.
    it("renders fallback text and undefined value when score is null", () => {
      render(<ScoreRing value={null} />)

      const meter = screen.getByRole("meter", { name: "Gluco Score" })
      expect(meter).not.toHaveAttribute("aria-valuenow")
      expect(meter).toHaveAttribute("aria-valuetext", "No score yet")
      expect(screen.getByText("—")).toBeInTheDocument()
    })

    // Verifies that ScoreRing clamps out-of-boundary scores into the 0 to 100 range.
    it("clamps score values exceeding 100 or falling below 0", () => {
      const { rerender } = render(<ScoreRing value={120} />)
      expect(screen.getByRole("meter", { name: "Gluco Score" })).toHaveAttribute("aria-valuenow", "100")

      rerender(<ScoreRing value={-15} />)
      expect(screen.getByRole("meter", { name: "Gluco Score" })).toHaveAttribute("aria-valuenow", "0")
    })

    // Verifies plain-language trend descriptions for positive, negative, steady, and null changes.
    it("formats friendlyChange text correctly across point variations", () => {
      expect(friendlyChange(null)).toBe("We need a full day of readings before we can compare.")
      expect(friendlyChange(1)).toBe("Up 1 point since this time yesterday.")
      expect(friendlyChange(3.2)).toBe("Up 3 points since this time yesterday.")
      expect(friendlyChange(-1)).toBe("Down 1 point since this time yesterday.")
      expect(friendlyChange(-4.8)).toBe("Down 5 points since this time yesterday.")
      expect(friendlyChange(0.4)).toBe("About the same as this time yesterday.")
      expect(friendlyChange(-0.4)).toBe("About the same as this time yesterday.")
    })

    // Verifies that ChangeBadge displays points with proper sign and fallback for null.
    it("renders ChangeBadge with signed points and handles null comparison", () => {
      const { rerender } = render(<ChangeBadge change={4.2} />)
      expect(screen.getByText("+4.2 pts vs 24 h prior")).toBeInTheDocument()

      rerender(<ChangeBadge change={null} />)
      expect(screen.getByText("No 24 h comparison available")).toBeInTheDocument()
    })

    // Verifies that GlucoScore adapts formatting according to the patient or clinician audience.
    it("renders appropriate score summary layout based on audience prop", () => {
      const { rerender } = renderWithProviders(<GlucoScore value={82} change={2.1} audience="patient" />)
      expect(screen.getByText("Up 2 points since this time yesterday.")).toBeInTheDocument()
      expect(screen.getByText("Higher is healthier.")).toBeInTheDocument()

      rerender(<GlucoScore value={82} change={2.1} audience="clinician" />)
      expect(screen.getByText("+2.1 pts vs 24 h prior")).toBeInTheDocument()
    })
  })

  describe("PinnedWidgets", () => {
    const mockUnpinMutate = vi.fn()
    const samplePins = [
      {
        id: "pin-1",
        title: "Daily Heart Rate",
        kind: "trend" as const,
        query: { metrics: ["heart_rate"], hours: 72 },
        created_at: "2026-10-16T10:00:00Z",
      },
    ]

    beforeEach(() => {
      vi.mocked(useUnpinWidget).mockReturnValue({
        mutate: mockUnpinMutate,
        isPending: false,
      } as unknown as ReturnType<typeof useUnpinWidget>)
    })

    // Verifies that PinnedWidgets returns null when no widgets are pinned.
    it("returns null when pin collection is empty or undefined", () => {
      vi.mocked(usePinnedWidgets).mockReturnValue({
        data: [],
        isPending: false,
        isError: false,
      } as unknown as ReturnType<typeof usePinnedWidgets>)

      const { container } = renderWithProviders(<PinnedWidgets audience="patient" />)
      expect(container).toBeEmptyDOMElement()
    })

    // Verifies that PinnedWidgets renders pinned cards with title and query descriptions.
    it("renders pinned widget cards and kind descriptions when pins exist", () => {
      vi.mocked(usePinnedWidgets).mockReturnValue({
        data: samplePins,
        isPending: false,
        isError: false,
      } as unknown as ReturnType<typeof usePinnedWidgets>)
      vi.mocked(useWidgetData).mockReturnValue({
        data: undefined,
        isPending: true,
        isError: false,
      } as unknown as ReturnType<typeof useWidgetData>)

      renderWithProviders(<PinnedWidgets audience="patient" />)

      expect(screen.getByRole("heading", { name: "Pinned widgets" })).toBeInTheDocument()
      expect(screen.getByText("Daily Heart Rate")).toBeInTheDocument()
      expect(screen.getByText(/Trend · live, last 72 h/i)).toBeInTheDocument()
    })

    // Verifies that clicking the unpin button triggers the unpin mutation with the pin ID.
    it("triggers unpin mutation when unpin button is clicked", () => {
      vi.mocked(usePinnedWidgets).mockReturnValue({
        data: samplePins,
        isPending: false,
        isError: false,
      } as unknown as ReturnType<typeof usePinnedWidgets>)
      vi.mocked(useWidgetData).mockReturnValue({
        data: undefined,
        isPending: true,
        isError: false,
      } as unknown as ReturnType<typeof useWidgetData>)

      renderWithProviders(<PinnedWidgets audience="patient" />)

      const unpinBtn = screen.getByRole("button", { name: "Unpin Daily Heart Rate" })
      fireEvent.click(unpinBtn)

      expect(mockUnpinMutate).toHaveBeenCalledWith("pin-1", expect.any(Object))
    })

    // Verifies that an unpin mutation error calls toast.error with friendly message.
    it("displays error toast when unpin mutation encounters an error", () => {
      mockUnpinMutate.mockImplementationOnce((_id: string, options?: { onError?: (err: unknown) => void }) => {
        options?.onError?.(new ApiError(500, undefined, "Failed to unpin"))
      })

      vi.mocked(usePinnedWidgets).mockReturnValue({
        data: samplePins,
        isPending: false,
        isError: false,
      } as unknown as ReturnType<typeof usePinnedWidgets>)
      vi.mocked(useWidgetData).mockReturnValue({
        data: undefined,
        isPending: false,
        isError: false,
      } as unknown as ReturnType<typeof useWidgetData>)

      renderWithProviders(<PinnedWidgets audience="patient" />)

      const unpinBtn = screen.getByRole("button", { name: "Unpin Daily Heart Rate" })
      fireEvent.click(unpinBtn)

      expect(toast.error).toHaveBeenCalledWith("Something went wrong. Please try again.")
    })

    // Verifies that compliance note renders when a compliance step is present in widget data.
    it("renders compliance verification note with shield icon when present", () => {
      vi.mocked(usePinnedWidgets).mockReturnValue({
        data: samplePins,
        isPending: false,
        isError: false,
      } as unknown as ReturnType<typeof usePinnedWidgets>)
      vi.mocked(useWidgetData).mockReturnValue({
        data: {
          result: {
            metrics: ["heart_rate"],
            series: [{ display_name: "Self", points: [] }],
            start: "2026-10-13T10:00:00Z",
            end: "2026-10-16T10:00:00Z",
          },
          steps: [
            { stage: "compliance", text: "Checked against clinical protocol parameters" },
          ],
        },
        isPending: false,
        isError: false,
      } as unknown as ReturnType<typeof useWidgetData>)

      renderWithProviders(<PinnedWidgets audience="patient" />)

      expect(screen.getByText("Checked against clinical protocol parameters")).toBeInTheDocument()
    })
  })

  describe("WidgetView", () => {
    const sampleResult = {
      metrics: ["heart_rate"],
      series: [
        {
          display_name: "Patient A",
          points: [
            { t: "2026-10-15T00:00:00Z", heart_rate: 72 },
            { t: "2026-10-16T00:00:00Z", heart_rate: 76 },
          ],
        },
      ],
      start: "2026-10-15T00:00:00Z",
      end: "2026-10-16T00:00:00Z",
    } as unknown as QueryResult

    // Verifies that stat widget kind renders metric value and label.
    it("renders stat widget kind with primary value and metric label", () => {
      render(<WidgetView kind="stat" result={sampleResult} audience="patient" />)

      expect(screen.getByText("76.0")).toBeInTheDocument()
      expect(screen.getByText(/Heart Rate/)).toBeInTheDocument()
    })

    // Verifies that table widget kind renders series names and metric column headers.
    it("renders table widget kind with series rows and metric columns", () => {
      render(<WidgetView kind="table" result={sampleResult} audience="patient" />)

      expect(screen.getByText("Patient A")).toBeInTheDocument()
      expect(screen.getByText("Heart Rate")).toBeInTheDocument()
    })

    // Verifies that heatmap widget kind renders day labels and metric guidance note.
    it("renders heatmap widget kind with day timestamps and legend note", () => {
      render(<WidgetView kind="heatmap" result={sampleResult} audience="patient" />)

      expect(screen.getByText(/Heart Rate by day \(UTC\) · darker is higher/i)).toBeInTheDocument()
    })
  })
})
