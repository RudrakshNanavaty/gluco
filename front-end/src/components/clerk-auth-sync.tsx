"use client"

import { useAuth, useUser } from "@clerk/nextjs"
import { useRouter } from "next/navigation"
import { useEffect, useRef } from "react"
import { toast } from "sonner"

import { API_BASE_URL } from "@/lib/api/client"
import { homeFor, sessionStore } from "@/lib/session"
import type { Schemas } from "@/lib/api/client"

export function ClerkAuthSync() {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const { user } = useUser()
  const router = useRouter()
  const syncing = useRef(false)

  useEffect(() => {
    if (!isLoaded) return
    if (!isSignedIn) {
      if (sessionStore.get()) sessionStore.set(null)
      return
    }
    if (syncing.current) return

    const existingSession = sessionStore.get()
    if (existingSession && existingSession.expiresAt > Date.now()) return

    let cancelled = false
    syncing.current = true
    void (async () => {
      try {
        const clerkToken = await getToken(
          process.env.NEXT_PUBLIC_CLERK_JWT_TEMPLATE
            ? { template: process.env.NEXT_PUBLIC_CLERK_JWT_TEMPLATE }
            : undefined
        )
        if (!clerkToken || cancelled) return
        const response = await fetch(`${API_BASE_URL}/auth/clerk-login`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${clerkToken}`,
            ...(user?.username ? { "X-Clerk-Username": user.username } : {}),
          },
        })
        if (!response.ok) {
          let detail = "This Clerk account is not linked to a patient profile."
          try {
            const body = (await response.json()) as { detail?: string }
            if (body.detail) detail = body.detail
          } catch {
            // Keep the safe fallback message when the API did not return JSON.
          }
          toast.error("Patient sign-in could not be completed", {
            description: detail,
          })
          return
        }
        const data = (await response.json()) as {
          token: string
          expires_in: number
          principal: Schemas["PrincipalOut"]
        }
        if (cancelled) return
        sessionStore.set({
          token: data.token,
          principal: data.principal,
          expiresAt: Date.now() + data.expires_in * 1000,
        })
        const destination = homeFor(data.principal)
        if (window.location.pathname !== destination) router.replace(destination)
      } catch {
        if (!cancelled) {
          toast.error("Patient sign-in could not be completed", {
            description: "The Gluco API is unavailable. Please try again.",
          })
        }
      } finally {
        syncing.current = false
      }
    })()

    return () => {
      cancelled = true
    }
  }, [getToken, isLoaded, isSignedIn, router, user?.username])

  return null
}
