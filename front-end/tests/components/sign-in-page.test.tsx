import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import SignInPage from "@/app/page"
import { useHydrated, useSession } from "@/lib/auth"
import type { Session } from "@/lib/session"
import { createMockRouter } from "../test-utils"

const mockRouter = createMockRouter()
const clerk = vi.hoisted(() => ({
  isLoaded: true,
  isSignedIn: false,
  signOut: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}))

vi.mock("@clerk/nextjs", () => ({
  SignIn: () => <div data-testid="clerk-sign-in" />,
  useAuth: () => ({ isLoaded: clerk.isLoaded, isSignedIn: clerk.isSignedIn }),
  useClerk: () => ({ signOut: clerk.signOut }),
}))

vi.mock("@/lib/auth", () => ({
  useHydrated: vi.fn(),
  useSession: vi.fn(),
}))

describe("SignInPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clerk.isLoaded = true
    clerk.isSignedIn = false
    vi.mocked(useHydrated).mockReturnValue(true)
    vi.mocked(useSession).mockReturnValue(null)
  })

  it("offers only the Clerk sign-in form, with no persona picker", () => {
    render(<SignInPage />)

    expect(screen.getByTestId("clerk-sign-in")).toBeTruthy()
    expect(screen.queryByText(/who's looking today/i)).toBeNull()
  })

  it("waits for Clerk to load before showing the form", () => {
    clerk.isLoaded = false

    render(<SignInPage />)

    expect(screen.queryByTestId("clerk-sign-in")).toBeNull()
  })

  it("shows progress, and a way out, while a Clerk session is being exchanged", () => {
    clerk.isSignedIn = true

    render(<SignInPage />)

    expect(screen.queryByTestId("clerk-sign-in")).toBeNull()
    expect(screen.getByText("Use a different account")).toBeTruthy()
  })

  it("redirects a signed-in user to their role home", () => {
    const session: Session = {
      token: "tok-1",
      expiresAt: Date.now() + 60_000,
      principal: {
        user_id: "0b0b8a9e-4d3c-5f6a-8b7c-9d0e1f2a3b4c",
        display_name: "Dr. Priya Shah",
        role: "clinician",
        participant_id: null,
      },
    }
    vi.mocked(useSession).mockReturnValue(session)

    render(<SignInPage />)

    expect(mockRouter.replace).toHaveBeenCalledWith("/clinician")
  })
})
