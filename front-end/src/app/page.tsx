"use client";

import { SignIn } from "@clerk/nextjs";
import { ActivityIcon, ArrowRightIcon, ShieldCheckIcon, SparklesIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAppSession } from "@/lib/app-session";

export default function SignInPage() {
  const router = useRouter();
  const session = useAppSession();
  const home = session.status === "signed-in" ? session.home : null;
  const [preview, setPreview] = useState<"patient" | "clinician">("patient");

  useEffect(() => {
    if (home) router.replace(home);
  }, [home, router]);

  const signingIn = session.status !== "signed-out";
  const previewContent =
    preview === "patient"
      ? {
          title: "A calmer view of your day",
          description: "See your score, live signals, and what changed in plain language.",
          items: ["Your Gluco Score", "Wearable trends", "Personal assistant"],
        }
      : {
          title: "A sharper view of your panel",
          description: "Spot patterns across patients and move from signal to context quickly.",
          items: ["Panel overview", "Patient comparisons", "Explainable changes"],
        };

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
        <Card className="max-w-md overflow-hidden border-primary/15 bg-card/70 backdrop-blur-sm">
          <CardHeader className="gap-3 pb-3">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <SparklesIcon className="size-4 text-primary" />
                Explore Gluco
              </CardTitle>
              <div className="flex rounded-lg bg-muted p-0.5" aria-label="Preview role">
                {(["patient", "clinician"] as const).map((role) => (
                  <Button
                    key={role}
                    type="button"
                    size="xs"
                    variant={preview === role ? "secondary" : "ghost"}
                    aria-pressed={preview === role}
                    onClick={() => setPreview(role)}
                    className="capitalize transition-all duration-200"
                  >
                    {role}
                  </Button>
                ))}
              </div>
            </div>
            <p className="text-sm font-medium transition-all duration-200">
              {previewContent.title}
            </p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              {previewContent.description}
            </p>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 pt-0">
            <div className="flex h-12 items-end gap-1.5 rounded-lg bg-accent/40 px-3 py-2">
              {[28, 42, 34, 56, 45, 68, 61, 78, 70, 88].map((height, index) => (
                <span
                  key={index}
                  className="motion-safe:animate-pulse flex-1 rounded-full bg-primary/70"
                  style={{ height: `${height}%`, animationDelay: `${index * 80}ms` }}
                />
              ))}
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              {previewContent.items.map((item, index) => {
                const Icon = index === 0 ? ActivityIcon : index === 1 ? ShieldCheckIcon : SparklesIcon;
                return (
                  <div key={item} className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Icon className="size-3.5 shrink-0 text-primary" />
                    {item}
                  </div>
                );
              })}
            </div>
            <Button
              type="button"
              variant="ghost"
              className="group w-fit px-0 text-xs text-primary hover:bg-transparent hover:text-primary/80"
              onClick={() => setPreview((current) => (current === "patient" ? "clinician" : "patient"))}
            >
              Switch preview <ArrowRightIcon className="size-3.5 transition-transform duration-200 group-hover:translate-x-1" />
            </Button>
          </CardContent>
        </Card>
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
            {session.status === "signing-in" ? (
              <Button type="button" variant="ghost" onClick={session.signOut}>
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
