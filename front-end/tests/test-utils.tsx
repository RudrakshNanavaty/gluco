import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, type RenderOptions } from "@testing-library/react"
import type { ReactElement, ReactNode } from "react"
import { vi } from "vitest"

import { TooltipProvider } from "@/components/ui/tooltip"
import {
  AppSessionContext,
  homeFor,
  type AppSession,
  type Principal,
  type Role,
} from "@/lib/app-session"

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
        gcTime: 0,
      },
    },
  })
}

export { createMockRouter, mockRouter } from "./mock-router"

/** A signed-in app session for `role`, without Clerk. */
export function sessionAs(
  role: Role,
  overrides: Partial<Principal> = {}
): AppSession {
  const principal: Principal = {
    user_id: `${role}-1`,
    role,
    display_name: role === "clinician" ? "Dr. Test" : "Test Patient",
    participant_id: role === "patient" ? "pat-1" : null,
    ...overrides,
  }
  return {
    status: "signed-in",
    principal,
    home: homeFor(principal),
    signOut: vi.fn(),
  }
}

export function renderWithProviders(
  ui: ReactElement,
  options?: {
    queryClient?: QueryClient
    renderOptions?: Omit<RenderOptions, "wrapper">
    /** Sign in as this role, or pass a whole `session`. */
    role?: Role
    session?: AppSession
  }
) {
  const testQueryClient = options?.queryClient ?? createTestQueryClient()
  const session =
    options?.session ?? (options?.role ? sessionAs(options.role) : null)

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={testQueryClient}>
        <AppSessionContext.Provider value={session}>
          <TooltipProvider>{children}</TooltipProvider>
        </AppSessionContext.Provider>
      </QueryClientProvider>
    )
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...options?.renderOptions }),
    queryClient: testQueryClient,
  }
}
