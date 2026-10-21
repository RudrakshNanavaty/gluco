"use client"

import { useAuth, useClerk } from "@clerk/nextjs"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
} from "react"
import { toast } from "sonner"

import { api, setTokenSource, unwrap, type Schemas } from "@/lib/api/client"
import { keys } from "@/lib/api/queries"

export type Principal = Schemas["PrincipalOut"]
export type Role = Principal["role"]

export type AppSession = (
  | { status: "loading" | "signed-out" | "signing-in"; principal: null }
  | { status: "signed-in"; principal: Principal; home: string }
) & { signOut: () => void }

export function homeFor(principal: Principal): string {
  return principal.role === "clinician" ? "/clinician" : "/me"
}

/** Exported for tests, which provide a session without Clerk. */
export const AppSessionContext = createContext<AppSession | null>(null)

/**
 * Who is signed in. Clerk owns the session: this registers Clerk's token with
 * the API transport, asks the back-end who that user is (`GET /me`), clears
 * every cached query when the user changes, and signs out when the back-end
 * refuses even a fresh token.
 */
export function AppSessionProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const { isLoaded, isSignedIn, userId, getToken } = useAuth()
  const clerk = useClerk()
  const queryClient = useQueryClient()

  const signOut = useCallback(() => {
    void clerk.signOut({ redirectUrl: "/" })
  }, [clerk])

  const tokens = useMemo(
    () => ({
      token: (fresh: boolean) =>
        getToken(fresh ? { skipCache: true } : undefined),
      rejected: () => {
        toast.error("This account could not be signed in.")
        signOut()
      },
    }),
    [getToken, signOut]
  )
  // Set during render, not in an effect: children's first requests must
  // already carry the token.
  setTokenSource(isSignedIn ? tokens : null)

  // Nothing cached for one user may reach the next.
  const lastUser = useRef(userId)
  useEffect(() => {
    if (lastUser.current === userId) return
    lastUser.current = userId
    queryClient.clear()
  }, [userId, queryClient])

  const me = useQuery({
    queryKey: keys.me(userId),
    queryFn: () => unwrap(api.GET("/me")),
    enabled: isSignedIn === true,
    staleTime: Infinity,
  })

  const value = useMemo<AppSession>(() => {
    if (!isLoaded) return { status: "loading", principal: null, signOut }
    if (!isSignedIn) return { status: "signed-out", principal: null, signOut }
    if (!me.data) return { status: "signing-in", principal: null, signOut }
    return {
      status: "signed-in",
      principal: me.data,
      home: homeFor(me.data),
      signOut,
    }
  }, [isLoaded, isSignedIn, me.data, signOut])

  return (
    <AppSessionContext.Provider value={value}>
      {children}
    </AppSessionContext.Provider>
  )
}

export function useAppSession(): AppSession {
  const value = useContext(AppSessionContext)
  if (!value)
    throw new Error("useAppSession must be used inside <AppSessionProvider>")
  return value
}

/** The signed-in user's role, which picks each component's wording. */
export function useAudience(): Role {
  const session = useAppSession()
  if (session.status !== "signed-in")
    throw new Error("useAudience needs a signed-in session")
  return session.principal.role
}
