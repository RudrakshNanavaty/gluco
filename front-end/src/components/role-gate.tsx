"use client"

import { useRouter } from "next/navigation"
import { useEffect } from "react"

import { useAppSession, type Role } from "@/lib/app-session"

/**
 * Renders its children only for the given role and sends anyone else to their
 * own home. The server enforces scope regardless; this keeps patients from ever
 * rendering (and requesting) cohort-wide views.
 */
export function RoleGate({
  role,
  children,
}: {
  role: Role
  children: React.ReactNode
}) {
  const router = useRouter()
  const session = useAppSession()
  const signedIn = session.status === "signed-in"
  const allowed = signedIn && session.principal.role === role
  const home = signedIn ? session.home : null

  useEffect(() => {
    if (home && !allowed) router.replace(home)
  }, [home, allowed, router])

  return allowed ? children : null
}
