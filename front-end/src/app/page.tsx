"use client";

import { SignIn } from "@clerk/nextjs";
import {
  ActivityIcon,
  ArrowRightIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  HeartPulseIcon,
  LockKeyholeIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from "lucide-react";
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
  const [focus, setFocus] = useState<"score" | "trends" | "assistant">("score");
  const [showDetails, setShowDetails] = useState(false);

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
          metric: "82",
          metricLabel: "steady today",
        }
      : {
          title: "A sharper view of your panel",
          description: "Spot patterns across patients and move from signal to context quickly.",
          items: ["Panel overview", "Patient comparisons", "Explainable changes"],
          metric: "17",
          metricLabel: "patients monitored",
        };

  const insight = {
    score: "Your score is trending steadily over the last 24 hours.",
    trends: "Small changes in movement and sleep are easy to spot here.",
    assistant: "Ask questions about your readings and get a plain-language answer.",
  }[focus];

  return (
    <main className="relative mx-auto grid w-full max-w-7xl flex-1 gap-10 overflow-hidden rounded-[2rem] bg-gradient-to-br from-background via-background to-primary/5 px-4 py-6 sm:px-6 sm:py-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16 lg:px-10">
      <div className="pointer-events-none absolute -right-32 -top-32 size-80 rounded-full bg-primary/10 blur-3xl" />
      <nav className="relative z-10 col-span-full flex items-center justify-between border-b border-border/60 pb-5" aria-label="Main navigation">
        <Brand />
        <div className="hidden items-center gap-1 rounded-full border border-border/70 bg-background/70 p-1 text-sm text-muted-foreground shadow-sm backdrop-blur sm:flex">
          <a className="transition-colors hover:text-foreground" href="#how-it-works">How it works</a>
          <a className="transition-colors hover:text-foreground" href="#security">Security</a>
          <a className="rounded-full bg-primary px-4 py-2 font-medium text-primary-foreground transition-opacity hover:opacity-90" href="#sign-in">Sign in</a>
        </div>
      </nav>
      <header className="relative z-10 flex flex-col gap-8 lg:sticky lg:top-16 lg:self-start">
        <div className="flex flex-col gap-4">
          <div className="flex w-fit items-center gap-2 rounded-full border border-primary/15 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary">
            <SparklesIcon className="size-3.5" /> AI-assisted health intelligence
          </div>
          <h1 className="text-4xl leading-[1.05] font-bold tracking-tight text-balance sm:text-5xl">
            Health insights that feel human.
          </h1>
          <p className="max-w-md text-lg text-muted-foreground">
            Gluco turns everyday wearable signals into clear, actionable context
            for people at risk of diabetes and the care teams supporting them.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground" id="security">
          <span className="flex items-center gap-1.5 rounded-full bg-muted px-3 py-1.5"><LockKeyholeIcon className="size-3.5" /> Private by design</span>
          <span className="flex items-center gap-1.5 rounded-full bg-muted px-3 py-1.5"><ShieldCheckIcon className="size-3.5" /> Explainable insights</span>
        </div>
        <p className="max-w-md text-xs text-muted-foreground">
          The Gluco Score is an estimate based on wearable data. It is not a
          blood sugar reading or a diagnosis.
        </p>
        <Button
          type="button"
          variant="outline"
          className="group w-fit rounded-full"
          onClick={() => document.getElementById("sign-in")?.scrollIntoView({ behavior: "smooth" })}
        >
          See your experience <ArrowRightIcon className="size-4 transition-transform duration-200 group-hover:translate-x-1" />
        </Button>
        <div className="relative overflow-hidden rounded-[1.75rem] border border-primary/15 bg-foreground p-5 text-background shadow-2xl shadow-primary/10">
          <div className="absolute -right-12 -top-12 size-36 rounded-full bg-primary/30 blur-2xl" />
          <div className="relative flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-background/60">Today&apos;s signal</p>
              <p className="mt-2 text-3xl font-semibold tracking-tight">Feeling balanced</p>
            </div>
            <div className="flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/30">
              <HeartPulseIcon className="size-7" />
            </div>
          </div>
          <div className="relative mt-6 grid grid-cols-3 gap-2">
            {["82 score", "7h 42m sleep", "Low stress"].map((label, index) => (
              <div key={label} className="rounded-xl border border-background/10 bg-background/10 px-3 py-3 backdrop-blur">
                <div className="mb-2 h-1.5 rounded-full bg-primary/80" style={{ width: `${[82, 68, 54][index]}%` }} />
                <p className="text-[11px] text-background/70">{label}</p>
              </div>
            ))}
          </div>
          <p className="relative mt-4 text-xs leading-relaxed text-background/65">Your signals are translated into a calm, explainable view—not another chart to decode.</p>
        </div>
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
            <div className="flex items-center justify-between rounded-xl bg-primary/8 px-3 py-2">
              <div className="flex items-center gap-2">
                <div className="flex size-8 items-center justify-center rounded-full bg-primary/12 text-primary">
                  {preview === "patient" ? <HeartPulseIcon className="size-4" /> : <ActivityIcon className="size-4" />}
                </div>
                <div>
                  <p className="text-2xl font-semibold leading-none tracking-tight">{previewContent.metric}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">{previewContent.metricLabel}</p>
                </div>
              </div>
              <span className="flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400">
                <CheckCircle2Icon className="size-3.5" /> Live preview
              </span>
            </div>
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
            <div className="grid grid-cols-3 gap-1 rounded-lg bg-muted/70 p-1">
              {(["score", "trends", "assistant"] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={focus === item}
                  onClick={() => setFocus(item)}
                  className={`rounded-md px-2 py-1.5 text-[11px] capitalize transition-all duration-200 ${focus === item ? "bg-background font-medium text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                >
                  {item}
                </button>
              ))}
            </div>
            <p className="min-h-8 text-xs leading-relaxed text-muted-foreground transition-all duration-200">{insight}</p>
            <Button
              type="button"
              variant="ghost"
              className="group w-fit px-0 text-xs text-primary hover:bg-transparent hover:text-primary/80"
              onClick={() => setPreview((current) => (current === "patient" ? "clinician" : "patient"))}
            >
              Switch preview <ArrowRightIcon className="size-3.5 transition-transform duration-200 group-hover:translate-x-1" />
            </Button>
            <button
              type="button"
              id="how-it-works"
              onClick={() => setShowDetails((current) => !current)}
              aria-expanded={showDetails}
              className="flex items-center justify-between border-t border-border/60 pt-3 text-left text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              How Gluco turns signals into clarity
              <ChevronDownIcon className={`size-4 transition-transform duration-200 ${showDetails ? "rotate-180" : ""}`} />
            </button>
            {showDetails ? (
              <div className="grid gap-2 text-xs text-muted-foreground">
                {["Collect wearable signals", "Explain meaningful changes", "Surface the next best question"].map((step, index) => (
                  <div key={step} className="flex items-center gap-2">
                    <span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">{index + 1}</span>
                    {step}
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>
      </header>

      <div id="sign-in" className="relative z-10 flex scroll-mt-8 flex-col items-start gap-6 rounded-[1.75rem] border border-border/70 bg-background/85 p-5 shadow-xl shadow-primary/5 backdrop-blur sm:p-8">
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
