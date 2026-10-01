import { contract } from "@tests/support/search"
import { describe, expect, it } from "vitest"
import { ApiError } from "@/shared/api/api-error"
import { describeError, isErrorMessageKey } from "@/shared/errors/describe-error"

type ErrorCode = { readonly code: string; readonly status: number }

const codes = (contract("error-codes.json") as { codes: ErrorCode[] }).codes

describe("api error codes", () => {
  it.each(codes.map((entry) => [entry.code, entry.status] as const))(
    "%s has its own message",
    (code, status) => {
      expect(isErrorMessageKey(code)).toBe(true)
      expect(describeError(new ApiError({ status, code })).messageKey).toBe(code)
    },
  )
})
