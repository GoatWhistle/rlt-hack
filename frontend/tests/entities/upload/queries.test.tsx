import { QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import { lotSummary, stubGateway, uploadDetail, uploadSummary } from "@tests/support/gateway"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"
import type { UploadGateway } from "@/entities/upload/gateway"
import { UploadGatewayProvider } from "@/entities/upload/gateway-context"
import {
  sameButLocale,
  uploadKeys,
  useLot,
  useUpload,
  withProgress,
} from "@/entities/upload/queries"
import { createQueryClient } from "@/shared/api/query-client"
import { LocaleProvider, useLocale } from "@/shared/i18n/locale-provider"

function wrapperFor(gateway: UploadGateway) {
  const client = createQueryClient()
  return function Wrapper({ children }: { readonly children: ReactNode }) {
    return (
      <LocaleProvider initialLocale="en">
        <QueryClientProvider client={client}>
          <UploadGatewayProvider gateway={gateway}>{children}</UploadGatewayProvider>
        </QueryClientProvider>
      </LocaleProvider>
    )
  }
}

describe("upload queries", () => {
  it("key locale-dependent data by language", () => {
    expect(uploadKeys.lot("ru", "u1", "10")).not.toEqual(uploadKeys.lot("en", "u1", "10"))
    expect(
      sameButLocale(uploadKeys.lot("ru", "u1", "10"), uploadKeys.lot("en", "u1", "10")),
    ).toBe(true)
    expect(
      sameButLocale(uploadKeys.lot("ru", "u1", "9"), uploadKeys.lot("en", "u1", "10")),
    ).toBe(false)
    expect(sameButLocale(undefined, uploadKeys.list("en"))).toBe(false)
    expect(sameButLocale(uploadKeys.list("ru"), uploadKeys.detail("en", "u1"))).toBe(false)
  })

  it("follow progress through the light summary and reread the lots when done", async () => {
    const lots = [
      lotSummary("10", { status: "queued" }),
      lotSummary("11", { status: "queued" }),
    ]
    const processing = uploadDetail(lots, { processed: 0 })
    const done = uploadDetail(lots, { processed: 2 })
    const get = vi.fn().mockResolvedValueOnce(processing).mockResolvedValue(done)
    const summary = vi.fn(async () =>
      uploadSummary({
        total: 2,
        processed: 2,
        counts: { ready: 2, needsCheck: 0, noCandidates: 0, failed: 0 },
      }),
    )
    const { result } = renderHook(() => useUpload("u1"), {
      wrapper: wrapperFor(stubGateway({ get, summary })),
    })
    await waitFor(() => expect(summary).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(get).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(result.current.data?.processed).toBe(2))
    expect(result.current.data?.lots).toEqual(lots)
  })

  it("show newer progress without dropping the known lots", () => {
    const detail = uploadDetail([lotSummary("10")], { processed: 0 })
    const ahead = uploadSummary({ processed: 1 })
    expect(withProgress(detail, ahead)).toMatchObject({ processed: 1, lots: detail.lots })
    expect(withProgress(detail, uploadSummary({ processed: 0 }))).toBe(detail)
    expect(withProgress(undefined, ahead)).toBeUndefined()
  })

  it("refetch a lot in the new language and keep showing it meanwhile", async () => {
    const lot = vi.fn(async () => ({ upload: uploadSummary(), lot: lotSummary("10") }))
    const gateway = stubGateway({ lot })
    const { result } = renderHook(() => ({ query: useLot("u1", "10"), locale: useLocale() }), {
      wrapper: wrapperFor(gateway),
    })
    await waitFor(() => expect(result.current.query.isSuccess).toBe(true))
    act(() => result.current.locale.setLocale("ru"))
    expect(result.current.query.data?.lot.id).toBe("10")
    await waitFor(() => expect(lot).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(result.current.query.isPlaceholderData).toBe(false))
  })
})
