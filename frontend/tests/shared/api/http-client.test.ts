import { describe, expect, it, vi } from "vitest"
import { ApiError, isApiError } from "@/shared/api/api-error"
import { buildUrl, createHttpClient } from "@/shared/api/http-client"
import { createQueryClient, MAX_QUERY_RETRIES, shouldRetry } from "@/shared/api/query-client"
import { DEFAULT_API_BASE_URL, readEnv } from "@/shared/config/env"

const identity = (data: unknown) => data

function clientWith(response: Response | Error | DOMException) {
  const fetcher = vi.fn<typeof fetch>(() =>
    response instanceof Response ? Promise.resolve(response) : Promise.reject(response),
  )
  return { fetcher, client: createHttpClient({ baseUrl: "/api/", fetcher }) }
}

describe("buildUrl", () => {
  it("joins paths and drops empty query values", () => {
    expect(buildUrl("/api/", "/lots", { page: 2, q: "a b", skip: undefined, none: null })).toBe(
      "/api/lots?page=2&q=a+b",
    )
    expect(buildUrl("https://x.dev/api", "lots")).toBe("https://x.dev/api/lots")
  })
})

describe("http client", () => {
  it("sends json and returns the parsed body", async () => {
    const { client, fetcher } = clientWith(Response.json({ id: 1 }))
    const parse = vi.fn((data: unknown) => data as { id: number })
    await expect(client.post("/lots", { parse, body: { a: 1 } })).resolves.toEqual({ id: 1 })
    const [url, init] = fetcher.mock.calls[0] ?? []
    expect(url).toBe("/api/lots")
    expect(init).toMatchObject({ method: "POST", body: '{"a":1}' })
    expect(parse).toHaveBeenCalledWith({ id: 1 })
  })

  it("passes empty and text bodies to the parser", async () => {
    await expect(
      clientWith(new Response(null, { status: 204 })).client.get("/a", { parse: identity }),
    ).resolves.toBeNull()
    await expect(
      clientWith(new Response("plain")).client.get("/a", { parse: identity }),
    ).resolves.toBe("plain")
  })

  it("turns a server error body into an ApiError", async () => {
    const response = Response.json({ code: "lot_closed", message: "closed" }, { status: 409 })
    const error = await clientWith(response)
      .client.get("/a", { parse: identity })
      .catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 409,
      code: "lot_closed",
      message: "closed",
      isClientError: true,
    })
  })

  it("names an error by status when the body has no code", async () => {
    const error = await clientWith(new Response("oops", { status: 503 }))
      .client.get("/a", { parse: identity })
      .catch((e) => e)
    expect(error).toMatchObject({ status: 503, code: "http_503", isClientError: false })
  })

  it("reports network failures and timeouts as transport errors", async () => {
    const network = await clientWith(new TypeError("offline"))
      .client.get("/a", { parse: identity })
      .catch((e) => e)
    expect(network).toMatchObject({ status: 0, code: "network" })
    const timeout = new DOMException("slow", "TimeoutError")
    const timedOut = await clientWith(timeout)
      .client.get("/a", { parse: identity })
      .catch((e) => e)
    expect(timedOut).toMatchObject({ status: 0, code: "timeout" })
  })

  it("rethrows an abort untouched", async () => {
    const abort = new DOMException("stop", "AbortError")
    await expect(clientWith(abort).client.get("/a", { parse: identity })).rejects.toBe(abort)
  })
})

describe("query client", () => {
  it("does not retry client errors and caps other retries", () => {
    expect(shouldRetry(0, new ApiError({ status: 404, code: "x" }))).toBe(false)
    expect(shouldRetry(0, new ApiError({ status: 500, code: "x" }))).toBe(true)
    expect(shouldRetry(MAX_QUERY_RETRIES, new Error("x"))).toBe(false)
    expect(createQueryClient().getDefaultOptions().mutations?.retry).toBe(false)
  })

  it("recognises api errors", () => {
    expect([
      isApiError(new ApiError({ status: 0, code: "network" })),
      isApiError(new Error()),
    ]).toEqual([true, false])
  })
})

describe("env", () => {
  it("reads the api base url with a default", () => {
    expect(readEnv({ VITE_API_BASE_URL: " https://api.dev " }).apiBaseUrl).toBe(
      "https://api.dev",
    )
    expect(readEnv({ VITE_API_BASE_URL: "  " }).apiBaseUrl).toBe(DEFAULT_API_BASE_URL)
    expect(readEnv({}).apiBaseUrl).toBe(DEFAULT_API_BASE_URL)
  })
})
