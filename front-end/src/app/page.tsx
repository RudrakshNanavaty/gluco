"use client";

import { SignIn, useAuth as useClerkAuth, useClerk } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useHydrated, useSession } from "@/lib/auth";
import { homeFor } from "@/lib/session";

export default function SignInPage() {
  const router = useRouter();
  const hydrated = useHydrated();
  const { isLoaded, isSignedIn } = useClerkAuth();
  const { signOut } = useClerk();
  const session = useSession();

  useEffect(() => {
    if (session) router.replace(homeFor(session.principal));
  }, [session, router]);

  // Signed in with Clerk: the app token is being exchanged (see ClerkAuthSync).
  const signingIn = !hydrated || !isLoaded || isSignedIn || session !== null;

  return (
    <main className="mx-auto grid w-full max-w-6xl flex-1 gap-12 px-4 py-10 sm:px-6 sm:py-16 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
      <header className="flex flex-col gap-8 lg:sticky lg:top-16 lg:self-start">
        <Brand />
        <div className="flex flex-col gap-4">
          <h1 className="text-4xl leading-[1.05] font-bold tracking-tight text-balance sm:text-5xl">
            Your wearable, explained in plain language.
          </h1>
          <p className="max-w-md text-lg text-muted-foreground">
            Gluco turns your wearable&apos;s daily readings into a simple score
            and answers your questions about them, for people at risk of
            diabetes and their care team.
          </p>
        </div>
        <p className="max-w-md text-xs text-muted-foreground">
          The Gluco Score is an estimate based on wearable data. It is not a
          blood sugar reading or a diagnosis.
        </p>
      </header>

      <div className="flex flex-col items-start gap-6">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-semibold tracking-tight">Sign in</h2>
          <p className="text-sm text-muted-foreground">
            Use the username and password you were given. Patients see only
            their own data; clinicians see their whole panel.
          </p>
        </div>
        {signingIn ? (
          <div className="flex items-center gap-3">
            <Spinner aria-label="Signing you in" />
            {isSignedIn ? (
              <Button
                type="button"
                variant="ghost"
                onClick={() => void signOut({ redirectUrl: "/" })}
              >
                Use a different account
              </Button>
            ) : null}
          </div>
        ) : (
          <SignIn routing="hash" />
        )}
      </div>
    </main>
  );
}
