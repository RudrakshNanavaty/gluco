"use client"

import { SignIn } from "@clerk/nextjs"

import { Brand } from "@/components/brand"

/** Serve Clerk path navigation, then return through the role-aware landing page. */
export default function SignInRoute() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <section
        className="flex w-full max-w-md flex-col items-center gap-6"
        aria-labelledby="sign-in-heading"
      >
        <Brand />
        <h1 id="sign-in-heading" className="sr-only">
          Sign in to Gluco
        </h1>
        <SignIn
          routing="path"
          path="/sign-in"
          signUpUrl="/sign-up"
          fallbackRedirectUrl="/"
        />
      </section>
    </main>
  )
}
