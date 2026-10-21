import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import SignInRoute from "@/app/sign-in/[[...sign-in]]/page"

const clerk = vi.hoisted(() => ({
  signIn: vi.fn((props: Record<string, unknown>) => (
    <div data-testid="clerk-sign-in" data-path={props.path as string} />
  )),
  signUp: vi.fn((props: Record<string, unknown>) => (
    <div data-testid="clerk-sign-up" data-path={props.path as string} />
  )),
}))

vi.mock("@clerk/nextjs", () => ({ SignIn: clerk.signIn, SignUp: clerk.signUp }))

describe("configured Clerk path routes", () => {
  beforeEach(() => vi.clearAllMocks())

  it("serves existing-account sign-in without a registration link", () => {
    render(<SignInRoute />)
    expect(
      screen.getByRole("heading", { name: "Sign in to Gluco" })
    ).toBeTruthy()
    expect(screen.getByTestId("clerk-sign-in")).toBeTruthy()
    expect(screen.queryByTestId("clerk-sign-up")).toBeNull()
    expect(clerk.signIn.mock.calls[0]?.[0]).toMatchObject({
      routing: "path",
      path: "/sign-in",
      withSignUp: false,
      appearance: { elements: { footerAction: { display: "none" } } },
      fallbackRedirectUrl: "/",
    })
  })
})
