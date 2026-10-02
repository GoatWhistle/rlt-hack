import { renderHook } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import type { ReactNode } from "react"
import { describe, expect, it } from "vitest"
import { ApiError } from "@/shared/api/api-error"
import {
  describeError,
  isChunkLoadError,
  isErrorMessageKey,
  statusKey,
} from "@/shared/errors/describe-error"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { LocaleProvider } from "@/shared/i18n/locale-provider"

function routeResponse(status: number) {
  return { status, statusText: "", internal: false, data: null }
}

describe("describeError", () => {
  it("uses a known api code as the message key", () => {
    expect(describeError(new ApiError({ status: 0, code: "network" }))).toEqual({
      kind: "failure",
      messageKey: "network",
      code: "network",
      requestId: null,
    })
  })

  it("keeps the request number for support", () => {
    const error = new ApiError({
      status: 503,
      code: "storage_unavailable",
      requestId: "req-7f3a",
    })
    expect(describeError(error)).toMatchObject({
      code: "storage_unavailable",
      requestId: "req-7f3a",
    })
  })

  it("falls back to the status for unknown codes", () => {
    expect(describeError(new ApiError({ status: 403, code: "lot_locked" })).messageKey).toBe(
      "forbidden",
    )
    expect(describeError(new ApiError({ status: 502, code: "http_502" })).messageKey).toBe(
      "server",
    )
    expect(describeError(new ApiError({ status: 418, code: "teapot" })).messageKey).toBe(
      "unexpected",
    )
  })

  it("separates a missing route from other route failures", () => {
    expect(describeError(routeResponse(404))).toEqual({
      kind: "notFound",
      messageKey: "notFound",
      code: "http_404",
      requestId: null,
    })
    expect(describeError(routeResponse(500))).toMatchObject({
      kind: "failure",
      messageKey: "server",
    })
  })

  it("asks for a reload when a code chunk is gone", () => {
    const chunk = new TypeError("Failed to fetch dynamically imported module: /assets/home.js")
    expect(isChunkLoadError(chunk)).toBe(true)
    expect(describeError(chunk).kind).toBe("updateRequired")
  })

  it("treats anything else as unexpected", () => {
    expect(describeError(new Error("boom"))).toEqual({
      kind: "failure",
      messageKey: "unexpected",
      code: null,
      requestId: null,
    })
    expect(describeError("boom").code).toBeNull()
    expect(isChunkLoadError("ChunkLoadError")).toBe(false)
  })

  it("knows which codes have messages", () => {
    expect([isErrorMessageKey("timeout"), isErrorMessageKey("toString")]).toEqual([true, false])
    expect([statusKey(401), statusKey(429), statusKey(599)]).toEqual([
      "unauthorized",
      "rateLimited",
      "server",
    ])
  })
})

describe("useErrorMessage", () => {
  it("translates any error into the current language", () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <LocaleProvider initialLocale="en">{children}</LocaleProvider>
    )
    const { result } = renderHook(() => useErrorMessage(), { wrapper })
    expect(result.current(new ApiError({ status: 0, code: "timeout" }))).toBe(
      en("timeout", "errors"),
    )
    expect(result.current(null)).toBe(en("unexpected", "errors"))
  })
})
