import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest"

import {
  api,
  ApiError,
  friendlyError,
  OFFLINE_MESSAGE,
  send,
  setTokenSource,
  setTransport,
  unwrap,
} from "@/lib/api/client"

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
      detail: [
        { loc: ["body", "hours"], msg: "Input should be a valid integer" },
      ],
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
    const error = new ApiError(
      500,
      "internal_failure",
      "Postgres connection timeout at /db"
    )
    expect(friendlyError(error)).toBe("Something went wrong. Please try again.")
  })

  // Verifies preservation of custom client error message when code is unmapped
  it("returns custom client error message for unmapped status < 500 codes", () => {
    const error = new ApiError(
      422,
      "validation_error",
      "Invalid date format specified"
    )
    expect(friendlyError(error)).toBe("Invalid date format specified")
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

describe("send", () => {
  afterEach(() => {
    setTokenSource(null)
  })

  /** Answer requests with `statuses` in turn; returns each request's Authorization. */
  function serve(...statuses: number[]) {
    const seen: (string | null)[] = []
    const previous = setTransport(async (input, init) => {
      seen.push(new Request(input, init).headers.get("authorization"))
      return new Response("{}", { status: statuses.shift() ?? 200 })
    })
    onTestFinished(() => {
      setTransport(previous)
    })
    return seen
  }

  // Verifies every request carries the session token
  it("sends the session token with each request", async () => {
    const seen = serve(200)
    setTokenSource({ token: async () => "t1", rejected: vi.fn() })

    await api.GET("/catalog")

    expect(seen).toEqual(["Bearer t1"])
  })

  // Verifies a 401 is retried once with a fresh token, and then succeeds
  it("retries a 401 once with a fresh token", async () => {
    const seen = serve(401, 200)
    const rejected = vi.fn()
    setTokenSource({
      token: async (fresh) => (fresh ? "fresh" : "cached"),
      rejected,
    })

    const { response } = await api.GET("/catalog")

    expect(seen).toEqual(["Bearer cached", "Bearer fresh"])
    expect(response.status).toBe(200)
    expect(rejected).not.toHaveBeenCalled()
  })

  it("keeps bearer tokens when Request and init headers are both supplied", async () => {
    const seen = serve(401, 200)
    setTokenSource({
      token: async (fresh) => (fresh ? "fresh" : "cached"),
      rejected: vi.fn(),
    })
    const request = new Request("http://localhost:8000/catalog", {
      headers: { "X-Original": "value" },
    })

    const response = await send(request, {
      headers: { "X-Override": "value" },
    })

    expect(response.status).toBe(200)
    expect(seen).toEqual(["Bearer cached", "Bearer fresh"])
    expect(request.headers.get("authorization")).toBeNull()
  })

  // Verifies a refused fresh token ends the session
  it("ends the session when a fresh token is refused too", async () => {
    serve(401, 401)
    const rejected = vi.fn()
    setTokenSource({ token: async () => "t1", rejected })

    await api.GET("/catalog")

    expect(rejected).toHaveBeenCalledTimes(1)
  })

  // Verifies a signed-out request carries no token
  it("sends no token when no one is signed in", async () => {
    const seen = serve(200)

    await api.GET("/catalog")

    expect(seen).toEqual([null])
  })
})
