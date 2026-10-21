import { screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import SignInPage from "@/app/page"
import { AppSessionProvider } from "@/lib/app-session"
import { fakeApi, PENDING } from "../fake-api"
import { mockRouter, renderWithProviders } from "../test-utils"

const clerk = vi.hoisted(() => ({
  isLoaded: true,
  isSignedIn: false,
  signOut: vi.fn(),
}))

vi.mock("@clerk/nextjs", () => ({
  SignIn: (props: {
    withSignUp?: boolean
    appearance?: { elements?: { footerAction?: { display?: string } } }
  }) => (
    <div
      data-testid="clerk-sign-in"
      data-sign-up={String(props.withSignUp)}
      data-registration-display={
        props.appearance?.elements?.footerAction?.display
      }
    />
  ),
  useAuth: () => ({
    isLoaded: clerk.isLoaded,
    isSignedIn: clerk.isSignedIn,
    userId: clerk.isSignedIn ? "user_1" : null,
    getToken: async () => "token",
  }),
  useClerk: () => ({ signOut: clerk.signOut }),
}))

function renderPage() {
  return renderWithProviders(
    <AppSessionProvider>
      <SignInPage />
    </AppSessionProvider>
  )
}

describe("SignInPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clerk.isLoaded = true
    clerk.isSignedIn = false
  })

  it("offers only the Clerk sign-in form, with no persona picker", () => {
    renderPage()

    expect(screen.getByTestId("clerk-sign-in")).toHaveAttribute(
      "data-sign-up",
      "false"
    )
    expect(screen.getByTestId("clerk-sign-in")).toHaveAttribute(
      "data-registration-display",
      "none"
    )
    expect(screen.queryByText(/who's looking today/i)).toBeNull()
  })

  it("waits for Clerk to load before showing the form", () => {
    clerk.isLoaded = false

    renderPage()

    expect(screen.queryByTestId("clerk-sign-in")).toBeNull()
  })

  it("shows progress, and a way out, while the back-end confirms who it is", () => {
    clerk.isSignedIn = true
    fakeApi({ "GET /me": PENDING })

    renderPage()

    expect(screen.queryByTestId("clerk-sign-in")).toBeNull()
    screen.getByText("Use a different account").click()
    expect(clerk.signOut).toHaveBeenCalledWith({ redirectUrl: "/" })
  })

  it.each([
    { role: "clinician" as const, participant: null, home: "/clinician" },
    { role: "patient" as const, participant: "pat-1", home: "/me" },
  ])(
    "redirects a signed-in $role to their role home",
    async ({ role, participant, home }) => {
      clerk.isSignedIn = true
      fakeApi({
        "GET /me": {
          user_id: "0b0b8a9e-4d3c-5f6a-8b7c-9d0e1f2a3b4c",
          display_name: "Dr. Priya Shah",
          role,
          participant_id: participant,
        },
      })

      renderPage()

      await waitFor(() => expect(mockRouter.replace).toHaveBeenCalledWith(home))
    }
  )
})
