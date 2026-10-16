import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  homeFor,
  sessionStore,
  type Principal,
  type Session,
} from "@/lib/session"

const CLINICIAN: Principal = {
  user_id: "clinician:1",
  display_name: "Dr. Smith",
  role: "clinician",
  participant_id: null,
}

const PATIENT: Principal = {
  user_id: "patient:013",
  display_name: "Patient 013",
  role: "patient",
  participant_id: "013",
}

const VALID_SESSION: Session = {
  token: "jwt-test-token",
  principal: PATIENT,
  expiresAt: Date.now() + 3_600_000,
}

describe("homeFor", () => {
  // Verifies clinician route assignment
  it("routes clinician role to /clinician", () => {
    expect(homeFor(CLINICIAN)).toBe("/clinician")
  })

  // Verifies patient route assignment
  it("routes patient role to /me", () => {
    expect(homeFor(PATIENT)).toBe("/me")
  })
})

describe("sessionStore", () => {
  beforeEach(() => {
    window.localStorage.clear()
    sessionStore.set(null)
  })

  // Verifies initial null return when storage is empty
  it("returns null when no session is stored", () => {
    expect(sessionStore.get()).toBeNull()
  })

  // Verifies setting and retrieving a valid session
  it("persists and returns active unexpired session", () => {
    sessionStore.set(VALID_SESSION)
    expect(sessionStore.get()).toEqual(VALID_SESSION)
    expect(window.localStorage.getItem("gluco:session")).toContain("jwt-test-token")
  })

  // Verifies expired session token rejection
  it("returns null when stored session has expired", () => {
    const expiredSession: Session = {
      token: "expired-token",
      principal: PATIENT,
      expiresAt: Date.now() - 10_000,
    }
    window.localStorage.setItem("gluco:session", JSON.stringify(expiredSession))
    sessionStore.set(null)
    window.localStorage.setItem("gluco:session", JSON.stringify(expiredSession))
    expect(sessionStore.get()).toBeNull()
  })

  // Verifies handling of valid JSON that lacks required expiresAt field
  it("returns null when stored session is missing expiresAt", () => {
    window.localStorage.setItem(
      "gluco:session",
      JSON.stringify({ token: "token-without-expiry", principal: PATIENT })
    )
    sessionStore.set(null)
    window.localStorage.setItem(
      "gluco:session",
      JSON.stringify({ token: "token-without-expiry", principal: PATIENT })
    )
    expect(sessionStore.get()).toBeNull()
  })

  // Verifies handling of corrupted non-JSON storage data
  it("returns null when storage contains corrupted JSON", () => {
    window.localStorage.setItem("gluco:session", "invalid{json")
    sessionStore.set(null)
    window.localStorage.setItem("gluco:session", "invalid{json")
    expect(sessionStore.get()).toBeNull()
  })

  // Verifies clearing session deletes key from storage
  it("removes storage key when setting session to null", () => {
    sessionStore.set(VALID_SESSION)
    expect(window.localStorage.getItem("gluco:session")).not.toBeNull()

    sessionStore.set(null)
    expect(sessionStore.get()).toBeNull()
    expect(window.localStorage.getItem("gluco:session")).toBeNull()
  })

  // Verifies subscriber invocation on local session changes
  it("notifies subscribers when session is updated", () => {
    const listener = vi.fn()
    const unsubscribe = sessionStore.subscribe(listener)

    sessionStore.set(VALID_SESSION)
    expect(listener).toHaveBeenCalledTimes(1)

    sessionStore.set(null)
    expect(listener).toHaveBeenCalledTimes(2)

    unsubscribe()
  })

  // Verifies subscriber invocation on external storage events
  it("notifies subscribers when storage event matching key fires", () => {
    const listener = vi.fn()
    const unsubscribe = sessionStore.subscribe(listener)

    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "gluco:session",
      })
    )

    expect(listener).toHaveBeenCalledTimes(1)
    unsubscribe()
  })

  // Verifies external cross-tab storage clear resets active session to null
  it("resets session state when external storage event clears session", () => {
    sessionStore.set(VALID_SESSION)
    expect(sessionStore.get()).toEqual(VALID_SESSION)

    const listener = vi.fn()
    const unsubscribe = sessionStore.subscribe(listener)

    window.localStorage.removeItem("gluco:session")
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "gluco:session",
      })
    )

    expect(sessionStore.get()).toBeNull()
    expect(listener).toHaveBeenCalled()
    unsubscribe()
  })

  // Verifies storage events for other keys are ignored
  it("ignores storage events for unrelated keys", () => {
    const listener = vi.fn()
    const unsubscribe = sessionStore.subscribe(listener)

    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "unrelated:key",
      })
    )

    expect(listener).not.toHaveBeenCalled()
    unsubscribe()
  })

  // Verifies unsubscribe stops both local and window storage listener notifications
  it("removes listener callback and window storage event listener upon unsubscription", () => {
    const listener = vi.fn()
    const unsubscribe = sessionStore.subscribe(listener)

    unsubscribe()
    sessionStore.set(VALID_SESSION)
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "gluco:session",
      })
    )

    expect(listener).not.toHaveBeenCalled()
  })

  // Verifies resilience when localStorage throws exceptions (e.g. private browsing)
  it("handles storage write exceptions gracefully", () => {
    vi.spyOn(window.localStorage, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError")
    })

    expect(() => sessionStore.set(VALID_SESSION)).not.toThrow()
    expect(sessionStore.get()).toEqual(VALID_SESSION)

    vi.restoreAllMocks()
  })
})
