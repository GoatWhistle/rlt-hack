import { ApiError } from "./api-error"

export type QueryValue = string | number | boolean | null | undefined

export type Parser<T> = (data: unknown) => T

export type RequestOptions<T> = {
  readonly parse: Parser<T>
  readonly query?: Readonly<Record<string, QueryValue>>
  readonly body?: unknown
  readonly signal?: AbortSignal
}

export type HttpClientConfig = {
  readonly baseUrl: string
  readonly fetcher?: typeof fetch
  readonly language?: () => string
}

export type HttpClient = {
  readonly get: <T>(path: string, options: RequestOptions<T>) => Promise<T>
  readonly post: <T>(path: string, options: RequestOptions<T>) => Promise<T>
}

export function buildUrl(
  baseUrl: string,
  path: string,
  query?: Readonly<Record<string, QueryValue>>,
): string {
  const url = `${baseUrl.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== null && value !== undefined) params.append(key, String(value))
  }
  const search = params.toString()
  return search ? `${url}?${search}` : url
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text()
  if (text.length === 0) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function errorFrom(status: number, body: unknown): ApiError {
  const record =
    typeof body === "object" && body !== null ? (body as Record<string, unknown>) : {}
  const code = typeof record.code === "string" ? record.code : `http_${status}`
  const message = typeof record.message === "string" ? record.message : undefined
  return new ApiError({ status, code, message })
}

function errorName(cause: unknown): string {
  return typeof cause === "object" && cause !== null && "name" in cause
    ? String(cause.name)
    : ""
}

function transportError(cause: unknown): ApiError {
  const timedOut = errorName(cause) === "TimeoutError"
  return new ApiError({ status: 0, code: timedOut ? "timeout" : "network", cause })
}

function encodeBody(body: unknown): {
  readonly headers: Record<string, string>
  readonly body?: BodyInit
} {
  if (body === undefined) return { headers: { Accept: "application/json" } }
  if (body instanceof FormData) return { headers: { Accept: "application/json" }, body }
  return {
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }
}

function withLanguage(
  headers: Record<string, string>,
  language: string | undefined,
): Record<string, string> {
  return language ? { ...headers, "Accept-Language": language } : headers
}

const globalFetch: typeof fetch = (input, init) => fetch(input, init)

export function createHttpClient({
  baseUrl,
  fetcher = globalFetch,
  language,
}: HttpClientConfig): HttpClient {
  const request = async <T>(method: string, path: string, options: RequestOptions<T>) => {
    const encoded = encodeBody(options.body)
    let response: Response
    try {
      response = await fetcher(buildUrl(baseUrl, path, options.query), {
        method,
        ...encoded,
        headers: withLanguage(encoded.headers, language?.()),
        signal: options.signal,
      })
    } catch (cause) {
      if (errorName(cause) === "AbortError") throw cause
      throw transportError(cause)
    }
    const body = await readBody(response)
    if (!response.ok) throw errorFrom(response.status, body)
    return options.parse(body)
  }
  return {
    get: (path, options) => request("GET", path, options),
    post: (path, options) => request("POST", path, options),
  }
}
