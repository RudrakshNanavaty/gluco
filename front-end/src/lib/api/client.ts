import createClient from "openapi-fetch"

import type { components, paths } from "@/lib/api/schema"

export type Schemas = components["schemas"]

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "")

/** A failed API call. `code` is the back-end's stable error code when it sent one. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string | undefined,
    message: string,
    readonly body?: unknown
  ) {
    super(message)
    this.name = "ApiError"
  }

  static from(status: number, body: unknown): ApiError {
    const record = (body ?? {}) as { detail?: unknown; code?: unknown }
    const message =
      typeof record.detail === "string"
        ? record.detail
        : status === 0
          ? OFFLINE_MESSAGE
          : GENERIC_MESSAGE
    const code = typeof record.code === "string" ? record.code : undefined
    return new ApiError(status, code, message, body)
  }
}

export const OFFLINE_MESSAGE = "Can't connect to Gluco right now."
const GENERIC_MESSAGE = "Something went wrong. Please try again."

const CODE_MESSAGES: Record<string, string> = {
  not_found: "We couldn't find what you were looking for.",
  ambiguous: "More than one result matched. Please be more specific.",
  not_permitted: "You don't have access to that.",
  bad_query: "That request couldn't be completed. Please try something different.",
}

/** Plain-language text for any error, so raw server or network messages never reach the screen. */
export function friendlyError(error: unknown): string {
  if (!(error instanceof ApiError)) return GENERIC_MESSAGE
  if (error.status === 0) return OFFLINE_MESSAGE
  if (error.code && CODE_MESSAGES[error.code]) return CODE_MESSAGES[error.code]
  return error.status >= 500 ? GENERIC_MESSAGE : error.message
}

/** How requests reach the network: `fetch` in the app, a fake in tests. */
export type Transport = typeof fetch

let transport: Transport = (input, init) => fetch(input, init)

/** Send every API request, the SSE streams included, through `next`; returns the previous transport. */
export function setTransport(next: Transport): Transport {
  const previous = transport
  transport = next
  return previous
}

/** Where requests get their bearer token. The app session registers Clerk's. */
export type TokenSource = {
  /** The current token; `fresh` skips any cached one. */
  token(fresh: boolean): Promise<string | null>
  /** The back-end refused even a fresh token. */
  rejected(): void
}

let tokens: TokenSource | null = null

export function setTokenSource(next: TokenSource | null) {
  tokens = next
}

function authorized(
  input: RequestInfo | URL,
  init: RequestInit | undefined,
  token: string | null
): [RequestInfo | URL, RequestInit | undefined] {
  if (!token) return [input, init]
  const value = `Bearer ${token}`
  if (input instanceof Request) {
    // A copy, so the original (and its body) can be sent again on a retry.
    const request = input.clone()
    const headers = new Headers(init?.headers ?? request.headers)
    headers.set("Authorization", value)
    return [request, { ...init, headers }]
  }
  const headers = new Headers(init?.headers)
  headers.set("Authorization", value)
  return [input, { ...init, headers }]
}

/**
 * Send one request through the current transport, carrying the session token.
 * A 401 is retried once with a fresh token, since a cached one may have just
 * expired; a second 401 means the session is over.
 */
export const send: Transport = async (input, init) => {
  const source = tokens
  if (!source) return transport(input, init)
  const attempt = async (fresh: boolean) =>
    transport(...authorized(input, init, await source.token(fresh)))
  const response = await attempt(false)
  if (response.status !== 401) return response
  const retried = await attempt(true)
  if (retried.status === 401) source.rejected()
  return retried
}

export const api = createClient<paths>({ baseUrl: API_BASE_URL, fetch: send })

type Result<T> = { data?: T; error?: unknown; response: Response }

/** The response body, or an ApiError for anything that isn't a 2xx. */
export async function unwrap<T>(call: Promise<Result<T>>): Promise<T> {
  let result: Result<T>
  try {
    result = await call
  } catch (cause) {
    throw new ApiError(0, undefined, OFFLINE_MESSAGE, cause)
  }
  if (!result.response.ok || result.error !== undefined) {
    throw ApiError.from(result.response.status, result.error)
  }
  return result.data as T
}
