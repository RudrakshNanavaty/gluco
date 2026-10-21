// @vitest-environment happy-dom

import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import SignInRoute from "@/app/sign-in/[[...sign-in]]/page"
import SignUpRoute from "@/app/sign-up/[[...sign-up]]/page"

vi.mock("@clerk/nextjs", () => ({
  SignIn: () => <div data-testid="clerk-sign-in">Clerk sign in</div>,
  SignUp: () => <div data-testid="clerk-sign-up">Clerk sign up</div>,
}))

describe("Clerk authentication routes", () => {
  it("renders the configured sign-in route", () => {
    render(<SignInRoute />)

    expect(screen.getByRole("heading", { name: "Sign in to Gluco" })).toBeInTheDocument()
    expect(screen.getByTestId("clerk-sign-in")).toBeInTheDocument()
  })

  it("renders the configured sign-up route", () => {
    render(<SignUpRoute />)

    expect(screen.getByRole("heading", { name: "Create a Gluco account" })).toBeInTheDocument()
    expect(screen.getByTestId("clerk-sign-up")).toBeInTheDocument()
  })
})
