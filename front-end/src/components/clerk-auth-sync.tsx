"use client";

import { useAuth } from "@clerk/nextjs";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

import { api, friendlyError, unwrap } from "@/lib/api/client";
import { homeFor, sessionStore } from "@/lib/session";

/**
 * Exchanges a verified Clerk session for the app's own token. Clerk is the only
 * way in, so a Clerk sign-out also ends the app session.
 */
export function ClerkAuthSync() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const queryClient = useQueryClient();
  const router = useRouter();

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      if (sessionStore.get()) sessionStore.set(null);
      return;
    }
    const existing = sessionStore.get();
    if (existing && existing.expiresAt > Date.now()) return;

    let cancelled = false;
    void (async () => {
      try {
        const clerkToken = await getToken();
        if (!clerkToken || cancelled) return;
        const res = await unwrap(
          api.POST("/auth/clerk-login", {
            headers: { Authorization: `Bearer ${clerkToken}` },
          }),
        );
        if (cancelled) return;
        // Nothing cached for a previous user may leak into this one.
        queryClient.clear();
        sessionStore.set({
          token: res.token,
          principal: res.principal,
          expiresAt: Date.now() + res.expires_in * 1000,
        });
        const destination = homeFor(res.principal);
        if (window.location.pathname !== destination)
          router.replace(destination);
      } catch (error) {
        if (!cancelled) {
          toast.error("Sign-in could not be completed", {
            description: friendlyError(error),
          });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, isSignedIn, queryClient, router]);

  return null;
}
