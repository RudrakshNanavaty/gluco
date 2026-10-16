import { act, fireEvent, render, screen } from "@testing-library/react"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import PersonaPickerPage from "@/app/page"
import { usePersonas } from "@/lib/api/queries"
import { useAuth, useSession } from "@/lib/auth"
import type { Principal, Session } from "@/lib/session"
import { createMockRouter } from "../test-utils"

const mockRouter = createMockRouter()

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock("@/lib/api/queries", () => ({
  usePersonas: vi.fn(),
}))

vi.mock("@/lib/auth", () => ({
  useAuth: vi.fn(),
  useSession: vi.fn(),
}))

describe("PersonaPickerPage", () => {
  const mockLogin = vi.fn()
  const samplePersonas: Principal[] = [
    { user_id: "doc-1", display_name: "Dr. Stone", role: "clinician", participant_id: null },
    { user_id: "pat-1", display_name: "Alice Parker", role: "patient", participant_id: "pat-1" },
    { user_id: "pat-2", display_name: "Bob Vance", role: "patient", participant_id: "pat-2" },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuth).mockReturnValue({ login: mockLogin, logout: vi.fn() })
    vi.mocked(useSession).mockReturnValue(null)
    vi.mocked(usePersonas).mockReturnValue({
      data: samplePersonas,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof usePersonas>)
  })

  // Verifies that an already signed-in user is redirected directly to their designated dashboard route.
  it("redirects authenticated user to role home on mount", () => {
    const activeSession: Session = {
      token: "tok-1",
      expiresAt: Date.now() + 60_000,
      principal: { user_id: "doc-1", display_name: "Dr. Stone", role: "clinician", participant_id: null },
    }
    vi.mocked(useSession).mockReturnValue(activeSession)

    render(<PersonaPickerPage />)

    expect(mockRouter.replace).toHaveBeenCalledWith("/clinician")
  })

  // Verifies that skeleton placeholders render when the persona list is loading.
  it("renders loading skeletons when personas query is pending", () => {
    vi.mocked(usePersonas).mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as unknown as ReturnType<typeof usePersonas>)

    const { container } = render(<PersonaPickerPage />)

    const skeletons = container.querySelectorAll("[data-slot=skeleton], .animate-pulse")
    expect(skeletons.length).toBeGreaterThan(0)
    expect(screen.queryByText("Dr. Stone")).not.toBeInTheDocument()
  })

  // Verifies that a destructive error banner renders when loading personas fails.
  it("renders error alert banner when personas query fails", () => {
    vi.mocked(usePersonas).mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
    } as unknown as ReturnType<typeof usePersonas>)

    render(<PersonaPickerPage />)

    expect(screen.getByText("Can't load profiles")).toBeInTheDocument()
    expect(screen.getByText(/couldn't reach Gluco/i)).toBeInTheDocument()
  })

  // Verifies that personas are separated correctly into clinician and patient groups.
  it("renders clinician and patient groups with display names", () => {
    render(<PersonaPickerPage />)

    expect(screen.getByText("Clinician")).toBeInTheDocument()
    expect(screen.getByText("Dr. Stone")).toBeInTheDocument()
    expect(screen.getByText("Patients")).toBeInTheDocument()
    expect(screen.getByText("Alice Parker")).toBeInTheDocument()
    expect(screen.getByText("Bob Vance")).toBeInTheDocument()
  })

  // Verifies that clicking a persona button calls the login function with the persona ID.
  it("triggers login with selected persona user_id on click", async () => {
    mockLogin.mockResolvedValueOnce(undefined)

    render(<PersonaPickerPage />)

    const clinicianBtn = screen.getByRole("button", { name: /dr\. stone/i })
    await act(async () => {
      fireEvent.click(clinicianBtn)
    })

    expect(mockLogin).toHaveBeenCalledWith("doc-1")
  })

  // Verifies that pending spinner appears and sibling buttons disable while sign-in completes.
  it("disables buttons and sets pending spinner during sign-in", async () => {
    let resolveLogin: () => void = () => {}
    const loginPromise = new Promise<void>((resolve) => {
      resolveLogin = resolve
    })
    mockLogin.mockReturnValueOnce(loginPromise)

    render(<PersonaPickerPage />)

    const clinicianBtn = screen.getByRole("button", { name: /dr\. stone/i })
    const patientBtn = screen.getByRole("button", { name: /alice parker/i })

    await act(async () => {
      fireEvent.click(clinicianBtn)
    })

    expect(clinicianBtn).toBeDisabled()
    expect(patientBtn).toBeDisabled()

    await act(async () => {
      resolveLogin()
    })
  })

  // Verifies that failed login surfaces an error toast and re-enables interactive persona buttons.
  it("shows error toast and resets pending state when login fails", async () => {
    mockLogin.mockRejectedValueOnce(new Error("Network offline"))

    render(<PersonaPickerPage />)

    const clinicianBtn = screen.getByRole("button", { name: /dr\. stone/i })
    await act(async () => {
      fireEvent.click(clinicianBtn)
    })

    expect(toast.error).toHaveBeenCalledWith(
      "Couldn't sign you in as Dr. Stone.",
      expect.objectContaining({ description: expect.any(String) })
    )
    expect(clinicianBtn).not.toBeDisabled()
  })
})
