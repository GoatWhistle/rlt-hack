import { screen } from "@testing-library/react"
import {
  lotSummary,
  type PageOptions,
  renderPage,
  stubGateway,
  uploadDetail,
  uploadSummary,
} from "@tests/support/gateway"
import { vi } from "vitest"
import type { UploadGateway } from "@/entities/upload/gateway"
import type { LotDetail } from "@/entities/upload/model"
import { recommendationFixture } from "../../entities/recommendation/fixture"

export const LOTS = [
  lotSummary("9"),
  lotSummary("10", { title: "Food supply" }),
  lotSummary("11"),
]

export function lotDetail(overrides: Partial<LotDetail> = {}): LotDetail {
  return {
    upload: uploadSummary(),
    lot: LOTS[1] ?? lotSummary("10"),
    recommendation: recommendationFixture,
    ...overrides,
  }
}

export function lotGateway(
  detail: LotDetail = lotDetail(),
  extra: Partial<UploadGateway> = {},
) {
  return stubGateway({
    get: vi.fn(async () => uploadDetail(LOTS)),
    lot: vi.fn(async () => detail),
    ...extra,
  })
}

export async function openLot(
  detail?: LotDetail,
  options: PageOptions & { readonly path?: string } = {},
) {
  const gateway = lotGateway(detail)
  const view = renderPage(options.path ?? "/uploads/u1/lots/10", gateway, options)
  await view.findByRole("heading", { level: 1 })
  return { ...view, gateway }
}

export function panel(name: string | RegExp) {
  return screen.getByRole("article", { name })
}
