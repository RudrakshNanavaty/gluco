import { render, screen } from "@testing-library/react"
import { act } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { RoleGate } from "@/components/role-gate"
import { sessionStore } from "@/lib/session"
import { createMockRouter } from "../test-utils"

const mockRouter = createMockRouter()

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}))

describe("RoleGate", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    act(() => {
      sessionStore.set(null)
    })
  })

  afterEach(() => {
    act(() => {
      sessionStore.set(null)
    })
  })

  // Verifies that child content renders when the active session role matches the clinician role.
  it("renders children when the session role matches clinician", () => {
    act(() => {
      sessionStore.set({
        token: "tok-1",
        expiresAt: Date.now() + 60_000,
        principal: { user_id: "doc-1", display_name: "Dr. Stone", role: "clinician", participant_id: null },
      })
      render(
        <RoleGate role="clinician">
          <div data-testid="clinician-content">Clinician Portal</div>
        </RoleGate>
      )
    })

    expect(screen.getByTestId("clinician-content")).toBeInTheDocument()
    expect(mockRouter.replace).not.toHaveBeenCalled()
  })

  // Verifies that child content renders when the active session role matches the patient role.
  it("renders children when the session role matches patient", () => {
    act(() => {
      sessionStore.set({
        token: "tok-2",
        expiresAt: Date.now() + 60_000,
        principal: { user_id: "pat-1", display_name: "Alice", role: "patient", participant_id: "pat-1" },
      })
      render(
        <RoleGate role="patient">
          <div data-testid="patient-content">Patient Portal</div>
        </RoleGate>
      )
    })

    expect(screen.getByTestId("patient-content")).toBeInTheDocument()
    expect(mockRouter.replace).not.toHaveBeenCalled()
  })

  // Verifies that children do not render and no redirection occurs when unauthenticated.
  it("renders null and does not redirect when session is null", () => {
    let container: HTMLElement
    act(() => {
      sessionStore.set(null)
      const res = render(
        <RoleGate role="clinician">
          <div data-testid="protected">Secret</div>
        </RoleGate>
      )
      container = res.container
    })

    expect(container!).toBeEmptyDOMElement()
    expect(mockRouter.replace).not.toHaveBeenCalled()
  })

  // Verifies that mismatched patient role redirects to /me and hides clinician children.
  it("redirects patient to /me when accessing clinician gate", () => {
    let container: HTMLElement
    act(() => {
      sessionStore.set({
        token: "tok-3",
        expiresAt: Date.now() + 60_000,
        principal: { user_id: "pat-2", display_name: "Bob", role: "patient", participant_id: "pat-2" },
      })
      const res = render(
        <RoleGate role="clinician">
          <div data-testid="protected">Clinician Only</div>
        </RoleGate>
      )
      container = res.container
    })

    expect(container!).toBeEmptyDOMElement()
    expect(mockRouter.replace).toHaveBeenCalledWith("/me")
  })

  // Verifies that mismatched clinician role redirects to /clinician when accessing patient gate.
  it("redirects clinician to /clinician when accessing patient gate", () => {
    let container: HTMLElement
    act(() => {
      sessionStore.set({
        token: "tok-4",
        expiresAt: Date.now() + 60_000,
        principal: { user_id: "doc-2", display_name: "Dr. Reed", role: "clinician", participant_id: null },
      })
      const res = render(
        <RoleGate role="patient">
          <div data-testid="protected">Patient Only</div>
        </RoleGate>
      )
      container = res.container
    })

    expect(container!).toBeEmptyDOMElement()
    expect(mockRouter.replace).toHaveBeenCalledWith("/clinician")
  })

  // Verifies dynamic reaction when session state changes while the component remains mounted.
  it("re-evaluates gate and triggers redirect when session updates", () => {
    let rerenderFn: (ui: React.ReactNode) => void
    act(() => {
      sessionStore.set({
        token: "tok-5",
        expiresAt: Date.now() + 60_000,
        principal: { user_id: "doc-3", display_name: "Dr. Jones", role: "clinician", participant_id: null },
      })
      const res = render(
        <RoleGate role="clinician">
          <div data-testid="content">Allowed Content</div>
        </RoleGate>
      )
      rerenderFn = res.rerender
    })

    expect(screen.getByTestId("content")).toBeInTheDocument()

    act(() => {
      sessionStore.set({
        token: "tok-6",
        expiresAt: Date.now() + 60_000,
        principal: { user_id: "pat-3", display_name: "Charlie", role: "patient", participant_id: "pat-3" },
      })
      rerenderFn(
        <RoleGate role="clinician">
          <div data-testid="content">Allowed Content</div>
        </RoleGate>
      )
    })

    expect(screen.queryByTestId("content")).not.toBeInTheDocument()
    expect(mockRouter.replace).toHaveBeenCalledWith("/me")
  })
})
