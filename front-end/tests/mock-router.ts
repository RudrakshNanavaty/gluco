import { vi } from "vitest"

// Kept apart from test-utils.tsx: vitest.setup.ts imports this before any test
// file's vi.mock runs, so it must not pull in app modules (such as Clerk).

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
