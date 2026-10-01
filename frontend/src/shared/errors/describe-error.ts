import { isRouteErrorResponse } from "react-router"
import { isApiError } from "@/shared/api/api-error"
import { type Resources, resources } from "@/shared/i18n/resources"

export type ErrorMessageKey = keyof Resources["errors"]

export type ErrorKind = "notFound" | "updateRequired" | "failure"

export type ErrorDescription = {
  readonly kind: ErrorKind
  readonly messageKey: ErrorMessageKey
  readonly code: string | null
}

export const STATUS_KEYS: Readonly<Record<number, ErrorMessageKey>> = {
  0: "network",
  400: "badRequest",
  401: "unauthorized",
  403: "forbidden",
  404: "notFound",
  409: "conflict",
  422: "badRequest",
  429: "rateLimited",
}

const CHUNK_FAILURE =
  /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module|ChunkLoadError/i

export function isErrorMessageKey(value: string): value is ErrorMessageKey {
  return Object.hasOwn(resources.en.errors, value)
}

export function statusKey(status: number): ErrorMessageKey {
  if (status >= 500) return "server"
  return STATUS_KEYS[status] ?? "unexpected"
}

export function isChunkLoadError(error: unknown): boolean {
  return error instanceof Error && CHUNK_FAILURE.test(`${error.name} ${error.message}`)
}

function statusOf(error: unknown): number | null {
  if (isApiError(error)) return error.status
  if (isRouteErrorResponse(error)) return error.status
  return null
}

function codeOf(error: unknown): string | null {
  if (isApiError(error)) return error.code
  if (isRouteErrorResponse(error)) return `http_${error.status}`
  return null
}

export function describeError(error: unknown): ErrorDescription {
  const code = codeOf(error)
  if (isChunkLoadError(error)) return { kind: "updateRequired", messageKey: "unexpected", code }
  const status = statusOf(error)
  const kind: ErrorKind = isRouteErrorResponse(error) && status === 404 ? "notFound" : "failure"
  if (code && isErrorMessageKey(code)) return { kind, messageKey: code, code }
  return { kind, messageKey: status === null ? "unexpected" : statusKey(status), code }
}
