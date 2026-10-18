import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { RoleGate } from "@/components/role-gate"
import { AppSessionContext, type AppSession } from "@/lib/app-session"
import { mockRouter, sessionAs } from "../test-utils"

const SIGNING_IN: AppSession = {
  status: "signing-in",
  principal: null,
  signOut: vi.fn(),
}

function gate(role: "clinician" | "patient", session: AppSession) {
  return (
    <AppSessionContext.Provider value={session}>
      <RoleGate role={role}>
        <div data-testid="content">Portal</div>
      </RoleGate>
    </AppSessionContext.Provider>
  )
}

describe("RoleGate", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Verifies that child content renders when the session role matches the gate.
  it.each(["clinician", "patient"] as const)(
    "renders children when the session role matches %s",
    (role) => {
      render(gate(role, sessionAs(role)))

      expect(screen.getByTestId("content")).toBeInTheDocument()
      expect(mockRouter.replace).not.toHaveBeenCalled()
    }
  )

  // Verifies nothing renders, and nobody is redirected, before the session is known.
  it("renders nothing and does not redirect while signing in", () => {
    const { container } = render(gate("clinician", SIGNING_IN))

    expect(container).toBeEmptyDOMElement()
    expect(mockRouter.replace).not.toHaveBeenCalled()
  })

  // Verifies each role is sent to its own home from the other role's gate.
  it.each([
    ["patient", "clinician", "/me"],
    ["clinician", "patient", "/clinician"],
  ] as const)("redirects a %s away from the %s gate to %s", (role, gated, home) => {
    const { container } = render(gate(gated, sessionAs(role)))

    expect(container).toBeEmptyDOMElement()
    expect(mockRouter.replace).toHaveBeenCalledWith(home)
  })

  // Verifies the gate re-evaluates when the session changes.
  it("re-evaluates the gate and redirects when the session changes", () => {
    const { rerender } = render(gate("clinician", sessionAs("clinician")))
    expect(screen.getByTestId("content")).toBeInTheDocument()

    rerender(gate("clinician", sessionAs("patient")))

    expect(screen.queryByTestId("content")).not.toBeInTheDocument()
    expect(mockRouter.replace).toHaveBeenCalledWith("/me")
  })
})
