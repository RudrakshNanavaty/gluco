import { screen, waitFor } from "@testing-library/react"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { AppSessionProvider, useAppSession } from "@/lib/app-session"
import { fakeApi, PENDING, Reply } from "../fake-api"
import { createTestQueryClient, renderWithProviders } from "../test-utils"

vi.mock("sonner", () => ({ toast: { error: vi.fn() } }))

const clerk = vi.hoisted(() => ({
  isLoaded: true,
  isSignedIn: true as boolean,
  userId: "user_1" as string | null,
  getToken: vi.fn(),
  signOut: vi.fn(),
}))

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    isLoaded: clerk.isLoaded,
    isSignedIn: clerk.isSignedIn,
    userId: clerk.userId,
    getToken: clerk.getToken,
  }),
  useClerk: () => ({ signOut: clerk.signOut }),
}))

const CLINICIAN = {
  user_id: "0b0b8a9e-4d3c-5f6a-8b7c-9d0e1f2a3b4c",
  display_name: "Dr. Priya Shah",
  role: "clinician",
  participant_id: null,
}

function Status() {
  const session = useAppSession()
  return (
    <p>
      {session.status}
      {session.status === "signed-in" ? ` ${session.home}` : ""}
    </p>
  )
}

function renderSession(queryClient = createTestQueryClient()) {
  return renderWithProviders(
    <AppSessionProvider>
      <Status />
    </AppSessionProvider>,
    { queryClient }
  )
}

describe("AppSessionProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clerk.isLoaded = true
    clerk.isSignedIn = true
    clerk.userId = "user_1"
    clerk.getToken.mockImplementation(async (options?: { skipCache?: boolean }) =>
      options?.skipCache ? "fresh-token" : "cached-token"
    )
  })

  // Verifies the back-end is asked who the Clerk user is, with Clerk's token.
  it("signs in with Clerk's token and names the role's home", async () => {
    const api = fakeApi({ "GET /me": CLINICIAN })

    renderSession()

    expect(await screen.findByText("signed-in /clinician")).toBeInTheDocument()
    expect(api.calls[0].headers.get("authorization")).toBe("Bearer cached-token")
  })

  // Verifies a stale cached token recovers instead of leaving the user stuck.
  it("recovers from a 401 by retrying with a fresh token", async () => {
    fakeApi({
      "GET /me": ({ headers }) =>
        headers.get("authorization") === "Bearer fresh-token"
          ? CLINICIAN
          : new Reply(401, { detail: "Your session has ended." }),
    })

    renderSession()

    expect(await screen.findByText("signed-in /clinician")).toBeInTheDocument()
    expect(clerk.signOut).not.toHaveBeenCalled()
  })

  // Verifies an account the back-end refuses is signed out with a message.
  it("signs out when the back-end refuses even a fresh token", async () => {
    fakeApi({ "GET /me": new Reply(401, { detail: "Your session has ended." }) })

    renderSession()

    await waitFor(() => expect(clerk.signOut).toHaveBeenCalledWith({ redirectUrl: "/" }))
    expect(toast.error).toHaveBeenCalledWith("This account could not be signed in.")
  })

  // Verifies the states before a Principal is known.
  it("reports loading, signed-out and signing-in", async () => {
    fakeApi({ "GET /me": PENDING })
    clerk.isLoaded = false
    const { rerender } = renderSession()
    expect(screen.getByText("loading")).toBeInTheDocument()

    clerk.isLoaded = true
    clerk.isSignedIn = false
    clerk.userId = null
    rerender(
      <AppSessionProvider>
        <Status />
      </AppSessionProvider>
    )
    expect(screen.getByText("signed-out")).toBeInTheDocument()

    clerk.isSignedIn = true
    clerk.userId = "user_1"
    rerender(
      <AppSessionProvider>
        <Status />
      </AppSessionProvider>
    )
    expect(screen.getByText("signing-in")).toBeInTheDocument()
  })

  // Verifies nothing cached for one user is kept for the next.
  it("clears every cached query when the user changes", async () => {
    fakeApi({ "GET /me": CLINICIAN })
    const queryClient = createTestQueryClient()
    // Unobserved data would otherwise be collected at once (gcTime 0).
    queryClient.setQueryDefaults(["data"], { gcTime: Infinity })
    queryClient.setQueryData(["data", "cohort"], { participants: 17 })
    const { rerender } = renderSession(queryClient)
    await screen.findByText("signed-in /clinician")
    expect(queryClient.getQueryData(["data", "cohort"])).toBeDefined()

    clerk.userId = "user_2"
    rerender(
      <AppSessionProvider>
        <Status />
      </AppSessionProvider>
    )

    await waitFor(() =>
      expect(queryClient.getQueryData(["data", "cohort"])).toBeUndefined()
    )
  })
})
