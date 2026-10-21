import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import SignInRoute from "@/app/sign-in/[[...sign-in]]/page"
import SignUpRoute from "@/app/sign-up/[[...sign-up]]/page"

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

  it("serves the sign-in form and routes registration to the existing sign-up page", () => {
    render(<SignInRoute />)
    expect(
      screen.getByRole("heading", { name: "Sign in to Gluco" })
    ).toBeTruthy()
    expect(screen.getByTestId("clerk-sign-in")).toBeTruthy()
    expect(screen.queryByTestId("clerk-sign-up")).toBeNull()
    expect(clerk.signIn.mock.calls[0]?.[0]).toMatchObject({
      routing: "path",
      path: "/sign-in",
      signUpUrl: "/sign-up",
      fallbackRedirectUrl: "/",
    })
  })

  it("serves registration and returns completed authentication to the role-routing entry point", () => {
    render(<SignUpRoute />)
    expect(
      screen.getByRole("heading", { name: "Create a Gluco account" })
    ).toBeTruthy()
    expect(screen.getByTestId("clerk-sign-up")).toBeTruthy()
    expect(screen.queryByTestId("clerk-sign-in")).toBeNull()
    expect(clerk.signUp.mock.calls[0]?.[0]).toMatchObject({
      routing: "path",
      path: "/sign-up",
      signInUrl: "/sign-in",
      fallbackRedirectUrl: "/",
    })
  })
})
