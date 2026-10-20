import { fireEvent, render, screen } from "@testing-library/react"
import { useTheme } from "next-themes"
import { beforeEach, expect, it, vi } from "vitest"

import { ThemeToggle } from "@/components/theme-toggle"

vi.mock("next-themes", () => ({ useTheme: vi.fn() }))

const setTheme = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
})

it.each([
  ["light", "Switch to dark mode", "false", "dark"],
  ["dark", "Switch to light mode", "true", "light"],
])("describes and toggles the %s theme", (theme, label, pressed, next) => {
  vi.mocked(useTheme).mockReturnValue({
    resolvedTheme: theme,
    setTheme,
    themes: ["light", "dark"],
  })

  render(<ThemeToggle />)

  const toggle = screen.getByRole("button", { name: label })
  expect(toggle).toHaveAttribute("aria-pressed", pressed)
  fireEvent.click(toggle)
  expect(setTheme).toHaveBeenCalledWith(next)
})
