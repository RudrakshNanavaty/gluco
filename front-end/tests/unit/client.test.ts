import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  api,
  ApiError,
  authHeader,
  friendlyError,
  handleUnauthorized,
  OFFLINE_MESSAGE,
  unwrap,
} from "@/lib/api/client"
import { sessionStore, type Session } from "@/lib/session"

const MOCK_SESSION: Session = {
  token: "header-test-token",
  principal: {
    user_id: "patient:1",
    display_name: "Test Patient",
    role: "patient",
    participant_id: "1",
  },
  expiresAt: Date.now() + 3_600_000,
}

describe("ApiError", () => {
  // Verifies constructor assigns all error properties
  it("constructs instance with status, code, message, and body", () => {
    const error = new ApiError(404, "not_found", "Item missing", { id: 1 })
    expect(error.status).toBe(404)
    expect(error.code).toBe("not_found")
    expect(error.message).toBe("Item missing")
    expect(error.body).toEqual({ id: 1 })
    expect(error.name).toBe("ApiError")
  })

  // Verifies factory extracts string detail and code from response body
  it("extracts detail and code from response payload", () => {
    const error = ApiError.from(400, {
      detail: "Participant not found",
      code: "not_found",
    })
    expect(error.status).toBe(400)
    expect(error.code).toBe("not_found")
    expect(error.message).toBe("Participant not found")
  })

  // Verifies factory assigns offline message on status 0 without detail
  it("assigns offline message when status is 0 without detail", () => {
    const error = ApiError.from(0, {})
    expect(error.status).toBe(0)
    expect(error.message).toBe(OFFLINE_MESSAGE)
    expect(error.code).toBeUndefined()
  })

  // Verifies factory assigns generic fallback on server status without detail
  it("assigns generic message when status is non-zero without detail", () => {
    const error = ApiError.from(500, null)
    expect(error.status).toBe(500)
    expect(error.message).toBe("Something went wrong. Please try again.")
  })

  // Verifies handling of non-string detail arrays (e.g. FastAPI 422 validation errors)
  it("falls back to generic message when detail is an array or object", () => {
    const error = ApiError.from(422, {
      detail: [{ loc: ["body", "hours"], msg: "Input should be a valid integer" }],
    })
    expect(error.status).toBe(422)
    expect(error.message).toBe("Something went wrong. Please try again.")
  })

  // Verifies handling of primitive non-object response bodies (e.g. raw gateway 502 HTML)
  it("handles primitive string error bodies without throwing", () => {
    const error = ApiError.from(502, "Bad Gateway")
    expect(error.status).toBe(502)
    expect(error.message).toBe("Something went wrong. Please try again.")
  })
})

describe("friendlyError", () => {
  // Verifies fallback for non-ApiError exceptions
  it("returns generic message for non-ApiError inputs", () => {
    expect(friendlyError(new Error("Database crash"))).toBe(
      "Something went wrong. Please try again."
    )
    expect(friendlyError("raw string error")).toBe(
      "Something went wrong. Please try again."
    )
  })

  // Verifies offline message for status 0
  it("returns offline message for status 0 network errors", () => {
    const error = new ApiError(0, undefined, "Network failed")
    expect(friendlyError(error)).toBe("Can't connect to Gluco right now.")
  })

  // Verifies mapping of recognized backend error codes
  it("maps stable error codes to user-friendly copy", () => {
    expect(friendlyError(new ApiError(404, "not_found", "raw msg"))).toBe(
      "We couldn't find what you were looking for."
    )
    expect(friendlyError(new ApiError(400, "ambiguous", "raw msg"))).toBe(
      "More than one result matched. Please be more specific."
    )
    expect(friendlyError(new ApiError(403, "not_permitted", "raw msg"))).toBe(
      "You don't have access to that."
    )
    expect(friendlyError(new ApiError(400, "bad_query", "raw msg"))).toBe(
      "That request couldn't be completed. Please try something different."
    )
  })

  // Verifies internal error concealment for status 500 or higher
  it("conceals internal server error messages for status >= 500", () => {
    const error = new ApiError(500, "internal_failure", "Postgres connection timeout at /db")
    expect(friendlyError(error)).toBe("Something went wrong. Please try again.")
  })

  // Verifies preservation of custom client error message when code is unmapped
  it("returns custom client error message for unmapped status < 500 codes", () => {
    const error = new ApiError(422, "validation_error", "Invalid date format specified")
    expect(friendlyError(error)).toBe("Invalid date format specified")
  })
})

describe("authHeader", () => {
  beforeEach(() => {
    sessionStore.set(null)
  })

  // Verifies Authorization header generation when session token exists
  it("generates Bearer authorization header when session is active", () => {
    sessionStore.set(MOCK_SESSION)
    expect(authHeader()).toEqual({
      Authorization: "Bearer header-test-token",
    })
  })

  // Verifies empty header object when no session is active
  it("returns empty object when no session is active", () => {
    expect(authHeader()).toEqual({})
  })
})

describe("handleUnauthorized", () => {
  beforeEach(() => {
    sessionStore.set(MOCK_SESSION)
  })

  // Verifies session clearance on 401 unauthorized status
  it("clears active session store on 401 response", () => {
    handleUnauthorized(401)
    expect(sessionStore.get()).toBeNull()
  })

  // Verifies session preservation on non-401 status codes
  it("preserves active session store on other HTTP status codes", () => {
    handleUnauthorized(403)
    expect(sessionStore.get()).toEqual(MOCK_SESSION)

    handleUnauthorized(500)
    expect(sessionStore.get()).toEqual(MOCK_SESSION)
  })
})

describe("unwrap", () => {
  // Verifies successful resolution and data extraction
  it("returns data payload when response is ok", async () => {
    const mockCall = Promise.resolve({
      data: { score: 72 },
      response: new Response(null, { status: 200 }),
    })
    const result = await unwrap(mockCall)
    expect(result).toEqual({ score: 72 })
  })

  // Verifies network exception conversion into status 0 ApiError
  it("throws ApiError status 0 when request promise rejects", async () => {
    const mockCall = Promise.reject(new Error("Failed to fetch"))
    await expect(unwrap(mockCall)).rejects.toMatchObject({
      status: 0,
      message: OFFLINE_MESSAGE,
    })
  })

  // Verifies HTTP error conversion when response.ok is false
  it("throws ApiError when response is not ok", async () => {
    const mockCall = Promise.resolve({
      error: { detail: "Access denied", code: "not_permitted" },
      response: new Response(null, { status: 403 }),
    })
    await expect(unwrap(mockCall)).rejects.toMatchObject({
      status: 403,
      code: "not_permitted",
      message: "Access denied",
    })
  })

  // Verifies error handling when response.ok is true but error is defined
  it("throws ApiError when response.ok is true but error is defined", async () => {
    const mockCall = Promise.resolve({
      error: { detail: "Business rule violation", code: "bad_query" },
      response: new Response(null, { status: 200 }),
    })
    await expect(unwrap(mockCall)).rejects.toMatchObject({
      status: 200,
      code: "bad_query",
      message: "Business rule violation",
    })
  })
})

describe("api middleware", () => {
  beforeEach(() => {
    sessionStore.set(null)
  })

  // Verifies auth middleware onRequest hook automatically passes Bearer token to fetch
  it("attaches Authorization header to outgoing requests when session exists", async () => {
    sessionStore.set(MOCK_SESSION)
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 })
    )

    await api.GET("/catalog", { fetch: mockFetch })

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const request = mockFetch.mock.calls[0][0] as Request
    expect(request.headers.get("authorization")).toBe("Bearer header-test-token")
  })

  // Verifies auth middleware onResponse hook triggers sign out on 401 response
  it("clears session store when API responds with 401", async () => {
    sessionStore.set(MOCK_SESSION)
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Token expired" }), { status: 401 })
    )

    await api.GET("/catalog", { fetch: mockFetch })

    expect(sessionStore.get()).toBeNull()
  })
})
