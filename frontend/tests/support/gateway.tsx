import { QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, type RouteObject, RouterProvider } from "react-router"
import { vi } from "vitest"
import type { UploadGateway } from "@/entities/upload/gateway"
import { UploadGatewayProvider } from "@/entities/upload/gateway-context"
import type { LotSummary, UploadDetail, UploadSummary } from "@/entities/upload/model"
import { LotPage } from "@/pages/lot"
import { LotsPage } from "@/pages/lots"
import { LotsEntryPage } from "@/pages/lots-entry"
import { UploadsPage } from "@/pages/uploads"
import { createQueryClient } from "@/shared/api/query-client"
import type { Locale } from "@/shared/i18n/locale"
import { LocaleProvider } from "@/shared/i18n/locale-provider"
import { ToastProvider } from "@/shared/ui/toast"

export function lotSummary(id: string, overrides: Partial<LotSummary> = {}): LotSummary {
  return {
    id,
    title: `Purchase ${id}`,
    customerInn: "7800000001",
    startPrice: 1000,
    publishDate: "2025-02-03",
    status: "ready",
    products: 5,
    candidates: 3,
    ...overrides,
  }
}

export function uploadSummary(overrides: Partial<UploadSummary> = {}): UploadSummary {
  return {
    id: "u1",
    fileName: "notices.csv",
    createdAt: "2026-10-01T10:00:00.000Z",
    total: 3,
    processed: 3,
    counts: { ready: 2, needsCheck: 1, noCandidates: 0, failed: 0 },
    rejected: 0,
    stored: true,
    ...overrides,
  }
}

export function uploadDetail(
  lots: readonly LotSummary[],
  overrides: Partial<UploadDetail> = {},
): UploadDetail {
  return {
    ...uploadSummary({ total: lots.length, processed: lots.length }),
    lots,
    issues: [],
    ...overrides,
  }
}

export function stubGateway(overrides: Partial<UploadGateway> = {}): UploadGateway {
  return {
    maxNotices: 100,
    list: vi.fn(async () => []),
    get: vi.fn(async () => uploadDetail([])),
    create: vi.fn(async () => uploadSummary()),
    lot: vi.fn(async () => {
      throw new Error("no lot")
    }),
    results: vi.fn(async () => []),
    ...overrides,
  }
}

const pageRoutes: RouteObject[] = [
  { path: "/uploads", Component: UploadsPage },
  { path: "/uploads/:uploadId", Component: LotsPage },
  { path: "/uploads/:uploadId/lots/:lotId", Component: LotPage },
  { path: "/lots", Component: LotsEntryPage },
]

export type PageOptions = {
  readonly locale?: Locale
}

export function renderPage(path: string, gateway: UploadGateway, options: PageOptions = {}) {
  const router = createMemoryRouter(pageRoutes, { initialEntries: [path] })
  const user = userEvent.setup()
  const result = render(
    <LocaleProvider initialLocale={options.locale ?? "en"}>
      <QueryClientProvider client={createQueryClient()}>
        <ToastProvider>
          <UploadGatewayProvider gateway={gateway}>
            <RouterProvider router={router} />
          </UploadGatewayProvider>
        </ToastProvider>
      </QueryClientProvider>
    </LocaleProvider>,
  )
  return { ...result, user, router }
}
