"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useClerk } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useCallback, useSyncExternalStore } from "react";

import { sessionStore, type Session } from "@/lib/session";

const noop = () => () => {};

/** False during server render and hydration, true once running in the browser. */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
}

/** The signed-in user, or null. Always null until hydrated. */
export function useSession(): Session | null {
  return useSyncExternalStore(
    sessionStore.subscribe,
    sessionStore.get,
    () => null,
  );
}

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { signOut } = useClerk();

  const logout = useCallback(() => {
    sessionStore.set(null);
    queryClient.clear();
    void signOut({ redirectUrl: "/" });
    router.replace("/");
  }, [queryClient, router, signOut]);

  return { logout };
}
