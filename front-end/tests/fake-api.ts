import { onTestFinished } from "vitest"

import { setTransport } from "@/lib/api/client"

/** One request the fake API answered, for assertions. */
export type FakeRequest = {
  method: string
  path: string
  params: Record<string, string>
  query: URLSearchParams
  headers: Headers
  body: unknown
}

/** Return this from a route to answer with a non-2xx status. */
export class Reply {
  constructor(
    readonly status: number,
    readonly body: unknown
  ) {}
}

/** A reply that never arrives: the query stays pending. */
export const PENDING = () => new Promise<never>(() => {})

type Route =
  | ((request: FakeRequest) => unknown)
  | object
  | string
  | number
  | boolean
  | null
  | undefined

function json(status: number, body: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

/**
 * Serve API requests from a table for the rest of the test, through the same
 * transport the app uses, so the real query hooks, cache keys and invalidation
 * run. Keys are "METHOD /path/{param}"; a value is the JSON body, a `Reply`, a
 * `Response` (for streams), or a function of the request returning one of those. Requests no route matches stay
 * pending and are listed in `unmatched`.
 */
export function fakeApi(routes: Record<string, Route>) {
  const calls: FakeRequest[] = []
  const unmatched: string[] = []
  const table = Object.entries(routes).map(([key, reply]) => {
    const [method, pattern] = key.split(" ")
    const names: string[] = []
    const source = pattern.replace(/\{(\w+)\}/g, (_, name: string) => {
      names.push(name)
      return "([^/]+)"
    })
    return { method, names, regex: new RegExp(`^${source}$`), reply }
  })

  const previous = setTransport(async (input, init) => {
    const request = new Request(input, init)
    const url = new URL(request.url)
    const text = request.method === "GET" ? "" : await request.text()
    for (const route of table) {
      const match = route.method === request.method && route.regex.exec(url.pathname)
      if (!match) continue
      const fake: FakeRequest = {
        method: request.method,
        path: url.pathname,
        params: Object.fromEntries(
          route.names.map((name, i) => [name, decodeURIComponent(match[i + 1])])
        ),
        query: url.searchParams,
        headers: request.headers,
        body: text ? JSON.parse(text) : undefined,
      }
      calls.push(fake)
      const value =
        typeof route.reply === "function"
          ? await route.reply(fake)
          : route.reply
      if (value instanceof Response) return value
      return value instanceof Reply ? json(value.status, value.body) : json(200, value)
    }
    unmatched.push(`${request.method} ${url.pathname}`)
    return PENDING()
  })
  onTestFinished(() => {
    setTransport(previous)
  })
  return { calls, unmatched }
}
