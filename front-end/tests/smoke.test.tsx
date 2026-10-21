import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { formatReplayTime } from "@/lib/format"

describe("Front-end test harness", () => {
  it("renders a component to the DOM", () => {
    render(<div data-testid="test-node">Gluco Test Suite Active</div>)
    expect(screen.getByTestId("test-node")).toHaveTextContent(
      "Gluco Test Suite Active"
    )
  })

  it("resolves @/* path aliases cleanly", () => {
    expect(formatReplayTime(null)).toBe("—")
  })
})
