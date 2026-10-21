"use client"

import { SignUp } from "@clerk/nextjs"

import { Brand } from "@/components/brand"

/** Serve Clerk path navigation, then return through the role-aware landing page. */
export default function SignUpRoute() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <section
        className="flex w-full max-w-md flex-col items-center gap-6"
        aria-labelledby="sign-up-heading"
      >
        <Brand />
        <h1 id="sign-up-heading" className="sr-only">
          Create a Gluco account
        </h1>
        <SignUp
          routing="path"
          path="/sign-up"
          signInUrl="/sign-in"
          fallbackRedirectUrl="/"
        />
      </section>
    </main>
  )
}
