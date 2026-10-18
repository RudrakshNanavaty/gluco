import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, type RenderOptions } from "@testing-library/react"
import type { ReactElement, ReactNode } from "react"
import { vi } from "vitest"

import { TooltipProvider } from "@/components/ui/tooltip"

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

export function createMockRouter() {
  return {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }
}

/** The router every test sees: vitest.setup.ts mocks `useRouter` to return it. */
export const mockRouter = createMockRouter()

export function renderWithProviders(
  ui: ReactElement,
  options?: {
    queryClient?: QueryClient
    renderOptions?: Omit<RenderOptions, "wrapper">
  }
) {
  const testQueryClient = options?.queryClient ?? createTestQueryClient()

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={testQueryClient}>
        <TooltipProvider>{children}</TooltipProvider>
      </QueryClientProvider>
    )
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...options?.renderOptions }),
    queryClient: testQueryClient,
  }
}
