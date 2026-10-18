import { screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ReplayControls } from "@/components/replay-controls"
import { useClock } from "@/lib/clock"
import { renderWithProviders } from "../test-utils"

vi.mock("@/lib/clock", () => ({ useClock: vi.fn() }))

describe("ReplayControls", () => {
  beforeEach(() => {
    vi.mocked(useClock).mockReturnValue({
      connected: true,
      control: vi.fn(),
      clock: {
        now: "2026-10-04T07:00:00Z",
        playing: true,
        seconds_per_hour: 5,
        enabled: true,
        data_start: "2026-09-27T05:00:00Z",
        data_end: "2026-10-04T07:00:00Z",
        at_end: false,
      },
    })
  })

  // Verifies clinicians get the controls for the shared clock.
  it("lets clinicians play, pause and seek the demo time", () => {
    renderWithProviders(<ReplayControls />, { role: "clinician" })

    expect(screen.getByRole("button", { name: "Pause demo" })).toBeInTheDocument()
    expect(screen.getByRole("slider")).toBeInTheDocument()
  })

  // Verifies patients see the time but cannot move a clock everyone shares.
  it("shows patients the demo time without any controls", () => {
    renderWithProviders(<ReplayControls />, { role: "patient" })

    expect(screen.getByText("Data as of")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /demo$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("slider")).not.toBeInTheDocument()
  })
})
