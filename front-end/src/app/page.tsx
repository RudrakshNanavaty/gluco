"use client";

import { SignIn } from "@clerk/nextjs";
import {
  ActivityIcon,
  ArrowDownIcon,
  ArrowRightIcon,
  HeartPulseIcon,
  LockKeyholeIcon,
  MoonIcon,
  ShieldCheckIcon,
  SparklesIcon,
  StethoscopeIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type PointerEvent } from "react";

import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAppSession } from "@/lib/app-session";

import "./landing.css";

type Role = "patient" | "clinician";
type Signal = "score" | "sleep" | "activity";

const signals = {
  score: {
    label: "Gluco Score",
    value: "82",
    unit: "/ 100",
    change: "A steady day",
    description: "A simple estimate shaped by your wearable patterns.",
    icon: HeartPulseIcon,
  },
  sleep: {
    label: "Sleep",
    value: "7h 42m",
    unit: "last night",
    change: "Looking consistent",
    description: "See how your rest fits into the bigger picture.",
    icon: MoonIcon,
  },
  activity: {
    label: "Movement",
    value: "68",
    unit: "activity index",
    change: "Moving well",
    description: "Understand daily activity without chasing a single number.",
    icon: ActivityIcon,
  },
} as const;

const roleCopy = {
  patient: {
    eyebrow: "For you",
    heading: "Understand your day. Not just your data.",
    description:
      "A clear view of your score, the patterns behind it, and an assistant that helps you ask better questions.",
    points: ["Your score in context", "Wearable trends made clear", "Answers in everyday language"],
    icon: HeartPulseIcon,
  },
  clinician: {
    eyebrow: "For care teams",
    heading: "See the signal across your whole panel.",
    description:
      "Move from a patient overview to the details that matter, with explainable changes and consistent context.",
    points: ["A clear panel overview", "Patient-to-patient comparisons", "Context behind changes"],
    icon: StethoscopeIcon,
  },
} as const;

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function SignInPage() {
  const router = useRouter();
  const session = useAppSession();
  const home = session.status === "signed-in" ? session.home : null;
  const [role, setRole] = useState<Role>("patient");
  const [signal, setSignal] = useState<Signal>("score");
  const activeSignal = signals[signal];
  const activeRole = roleCopy[role];
  const RoleIcon = activeRole.icon;

  useEffect(() => {
    if (home) router.replace(home);
  }, [home, router]);

  function moveStage(event: PointerEvent<HTMLDivElement>) {
    if (event.pointerType === "touch") return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width - 0.5;
    const y = (event.clientY - bounds.top) / bounds.height - 0.5;
    event.currentTarget.style.setProperty("--stage-x", `${x * 15}deg`);
    event.currentTarget.style.setProperty("--stage-y", `${y * -13}deg`);
    event.currentTarget.style.setProperty("--glow-x", `${(x + 0.5) * 100}%`);
    event.currentTarget.style.setProperty("--glow-y", `${(y + 0.5) * 100}%`);
  }

  function resetStage(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.style.setProperty("--stage-x", "0deg");
    event.currentTarget.style.setProperty("--stage-y", "0deg");
  }

  return (
    <main className="landing-page">
      <div className="landing-hero">
        <div className="landing-hero-glow" aria-hidden />
        <div className="landing-shell">
          <nav className="landing-nav" aria-label="Main navigation">
            <div className="landing-brand"><Brand /></div>
            <button type="button" className="landing-nav-cta" onClick={() => scrollToSection("sign-in")}>Sign in <ArrowRightIcon className="size-4" /></button>
          </nav>

          <div className="landing-hero-grid">
            <div className="landing-intro">
              <span className="landing-kicker"><span className="landing-kicker-dot" />A clearer view of your health</span>
              <h1>Wellness has a <em>story.</em> Let&apos;s make sense of yours.</h1>
              <p className="landing-lede">Gluco turns everyday wearable signals into an understandable score, meaningful trends, and better questions for you and your care team.</p>
              <div className="landing-actions">
                <Button type="button" size="lg" className="landing-primary-action" onClick={() => scrollToSection("sign-in")}>Get started <ArrowRightIcon className="size-4" /></Button>
                <button type="button" className="landing-text-action" onClick={() => scrollToSection("experience")}>Explore the experience <ArrowDownIcon className="size-4" /></button>
              </div>
              <div className="landing-proof"><ShieldCheckIcon className="size-4" /><span>Private by design</span><span className="landing-proof-divider" /><SparklesIcon className="size-4" /><span>Insights in plain language</span></div>
            </div>

            <div className="landing-stage" onPointerMove={moveStage} onPointerLeave={resetStage} aria-label="Interactive illustrative health signals preview">
              <div className="landing-stage-grid" aria-hidden />
              <div className="landing-stage-inner">
                <div className="landing-orbit landing-orbit-one" aria-hidden />
                <div className="landing-orbit landing-orbit-two" aria-hidden />
                <div className="landing-orbit landing-orbit-three" aria-hidden />
                <div className="landing-orb" aria-hidden><div className="landing-orb-core"><span className="landing-orb-glyph"><HeartPulseIcon /></span><span>gluco</span></div></div>
                <div className="landing-stage-caption">THE BIGGER PICTURE <span>•</span> IN MOTION</div>
              </div>
              <button type="button" className={`landing-float-card landing-float-score ${signal === "score" ? "is-selected" : ""}`} onClick={() => setSignal("score")} aria-pressed={signal === "score"}>
                <span className="landing-float-icon"><HeartPulseIcon /></span><span><strong>Gluco Score</strong><small>82 / 100 · steady today</small></span>
              </button>
              <button type="button" className={`landing-float-card landing-float-sleep ${signal === "sleep" ? "is-selected" : ""}`} onClick={() => setSignal("sleep")} aria-pressed={signal === "sleep"}>
                <span className="landing-float-icon"><MoonIcon /></span><span><strong>Restful sleep</strong><small>7h 42m · last night</small></span>
              </button>
              <button type="button" className={`landing-float-card landing-float-activity ${signal === "activity" ? "is-selected" : ""}`} onClick={() => setSignal("activity")} aria-pressed={signal === "activity"}>
                <span className="landing-float-icon"><ActivityIcon /></span><span><strong>Movement</strong><small>In your daily rhythm</small></span>
              </button>
              <div className="landing-stage-hint">Select a signal to explore <ArrowRightIcon className="size-3.5" /></div>
            </div>
          </div>
        </div>
      </div>

      <section className="landing-experience landing-shell" id="experience" aria-labelledby="experience-title">
        <div className="landing-section-heading"><span className="landing-section-label">THE EXPERIENCE</span><h2 id="experience-title">A little more clarity, every day.</h2><p>Explore how Gluco connects the dots between your wearable signals and a more useful conversation about health.</p></div>
        <div className="landing-experience-grid">
          <div className="landing-focus-card">
            <div className="landing-focus-top"><span>AN ILLUSTRATIVE PREVIEW</span><span className="landing-live-indicator"><span /> Your signals</span></div>
            <div className="landing-focus-tabs" role="group" aria-label="Choose a health signal">
              {(Object.keys(signals) as Signal[]).map((key) => { const Icon = signals[key].icon; return <button key={key} type="button" className={signal === key ? "is-active" : ""} aria-pressed={signal === key} onClick={() => setSignal(key)}><Icon className="size-4" />{signals[key].label}</button>; })}
            </div>
            <div className="landing-focus-content" key={signal}>
              <div><span className="landing-focus-label">{activeSignal.label}</span><div className="landing-focus-value">{activeSignal.value}<small>{activeSignal.unit}</small></div><span className="landing-focus-change"><span />{activeSignal.change}</span></div>
              <div className="landing-focus-viz" aria-hidden><div className="landing-focus-viz-glow" /><svg viewBox="0 0 320 110" preserveAspectRatio="none"><defs><linearGradient id="signal-area" x1="0" y1="0" x2="0" y2="1"><stop stopColor="currentColor" stopOpacity=".23"/><stop offset="1" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs><path d="M0 80 C30 76 43 86 65 61 S102 63 123 52 S161 71 183 43 S223 57 246 37 S280 47 320 18 L320 110 L0 110Z" fill="url(#signal-area)"/><path d="M0 80 C30 76 43 86 65 61 S102 63 123 52 S161 71 183 43 S223 57 246 37 S280 47 320 18" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/></svg></div>
            </div>
            <p className="landing-focus-description">{activeSignal.description}</p>
          </div>

          <div className="landing-role-card">
            <div className="landing-role-switch" role="group" aria-label="Preview Gluco by role"><button type="button" aria-pressed={role === "patient"} className={role === "patient" ? "is-active" : ""} onClick={() => setRole("patient")}>For patients</button><button type="button" aria-pressed={role === "clinician"} className={role === "clinician" ? "is-active" : ""} onClick={() => setRole("clinician")}>For clinicians</button></div>
            <div className="landing-role-content" key={role}><span className="landing-role-icon"><RoleIcon /></span><span className="landing-section-label">{activeRole.eyebrow}</span><h3>{activeRole.heading}</h3><p>{activeRole.description}</p><ul>{activeRole.points.map((point) => <li key={point}><span><ArrowRightIcon className="size-3.5" /></span>{point}</li>)}</ul></div>
          </div>
        </div>
      </section>

      <section className="landing-access" id="sign-in" aria-labelledby="sign-in-title"><div className="landing-shell landing-access-grid"><div className="landing-access-copy"><span className="landing-section-label">YOUR SPACE, YOUR SIGNALS</span><h2 id="sign-in-title">Ready to see the full picture?</h2><p>Sign in to your own Gluco experience. Patients see their personal view; clinicians see their care panel.</p><div className="landing-access-trust"><LockKeyholeIcon className="size-4" /> Your account is protected by secure sign-in.</div><p className="landing-disclaimer">The Gluco Score is an estimate based on wearable data. It is not a blood sugar reading or a diagnosis.</p></div><div className="landing-signin-card">{session.status !== "signed-out" ? <div className="flex items-center gap-3"><Spinner aria-label="Signing you in" />{session.status === "signing-in" ? <Button type="button" variant="ghost" onClick={session.signOut}>Use a different account</Button> : null}</div> : <SignIn routing="hash" />}</div></div></section>
    </main>
  );
}
