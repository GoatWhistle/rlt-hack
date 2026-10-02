import { QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, RouterProvider } from "react-router"
import { vi } from "vitest"
import type { AnalyticsGateway } from "@/entities/analytics/gateway"
import { AnalyticsGatewayProvider } from "@/entities/analytics/gateway-context"
import type {
  Category,
  Overview,
  Problem,
  QualityReport,
  Ratio,
  Run,
  SnapshotMeta,
  SourceSummary,
  SourcesReport,
} from "@/entities/analytics/model"
import {
  AnalyticsLayout,
  CategoriesPage,
  OverviewPage,
  QualityPage,
  RecordsPage,
  SourcesPage,
} from "@/pages/analytics"
import { createQueryClient } from "@/shared/api/query-client"
import { LocaleProvider } from "@/shared/i18n/locale-provider"
import { ToastProvider } from "@/shared/ui/toast"

export function ratio(numerator: number, denominator: number, unknown = 0): Ratio {
  return {
    numerator,
    denominator,
    unknown,
    share: denominator === 0 ? null : numerator / denominator,
  }
}

export const meta: SnapshotMeta = {
  snapshotId: "s1",
  asOf: "2026-10-02T09:00:00Z",
  computedAt: "2026-10-02T09:00:05Z",
  definitionsVersion: "v1",
  delaySeconds: 5,
  warnings: [],
  policy: { offerDays: 7, registryDays: 30, periodDays: 30 },
}

export function category(
  code: string,
  parent = "",
  overrides: Partial<Category> = {},
): Category {
  return {
    code,
    name: code ? `Name ${code}` : "",
    parent,
    offers: 6,
    share: ratio(6, 10),
    companies: 3,
    verifiedSellers: ratio(5, 6),
    fresh: ratio(4, 6),
    priced: ratio(3, 6),
    searchable: ratio(0, 0),
    systemAssigned: 5,
    sourceReported: 1,
    ...overrides,
  }
}

export function source(id: string, overrides: Partial<SourceSummary> = {}): SourceSummary {
  return {
    sourceId: id,
    name: `Source ${id}`,
    providerName: id,
    sourceType: "directory",
    state: "ok",
    offers: 8,
    companies: 3,
    fresh: ratio(5, 7, 1),
    lastSuccessAt: "2026-10-01T09:00:00Z",
    lastAttemptAt: "2026-10-01T09:00:00Z",
    runs: 2,
    failedRuns: 1,
    ...overrides,
  }
}

export function run(id: string, overrides: Partial<Run> = {}): Run {
  return {
    runId: id,
    sourceId: "a",
    sourceName: "Source a",
    startedAt: "2026-10-01T09:00:00Z",
    finishedAt: "2026-10-01T09:05:00Z",
    durationSeconds: 300,
    status: "failed",
    suppliersExtracted: 2,
    offersExtracted: 4,
    errorMessage: "boom",
    ...overrides,
  }
}

export function overview(overrides: Partial<Overview> = {}): Overview {
  return {
    meta,
    offers: 10,
    companies: 4,
    composition: [
      { key: "directory", count: 8 },
      { key: "registry", count: 2 },
    ],
    fresh: ratio(6, 9, 1),
    searchable: ratio(7, 10),
    runsSuccess: ratio(1, 2),
    runsPartial: 1,
    attention: [
      { code: "source_failed", sourceId: "a", count: 1, total: 1 },
      { code: "no_category", count: 4, total: 10 },
    ],
    categories: [category("01"), category("", "")],
    sources: [source("a"), source("b", { state: "never_run", lastSuccessAt: undefined })],
    runs: [run("r1")],
    ...overrides,
  }
}

export const problem: Problem = {
  sourceId: "a",
  name: "Source a",
  offers: 8,
  noSupplier: 1,
  unverifiedSeller: 1,
  noCategory: 4,
  noPrice: 3,
  noAttributes: 2,
  stale: 5,
  unknownAge: 1,
}

export function quality(overrides: Partial<QualityReport> = {}): QualityReport {
  return {
    meta,
    offers: 10,
    fresh: ratio(6, 9, 1),
    priced: ratio(0, 0),
    age: [
      { key: "d1", count: 3 },
      { key: "unknown", count: 1 },
    ],
    availability: [{ key: "available", count: 6 }],
    problems: [problem],
    ...overrides,
  }
}

export function sourcesReport(overrides: Partial<SourcesReport> = {}): SourcesReport {
  return {
    meta,
    items: overview().sources,
    runs: [run("r1")],
    success: ratio(1, 2),
    partial: 1,
    ...overrides,
  }
}

export function stubAnalytics(overrides: Partial<AnalyticsGateway> = {}): AnalyticsGateway {
  return {
    overview: vi.fn(async () => overview()),
    categories: vi.fn(async () => ({
      meta,
      offers: 10,
      items: [category("01"), category("01.11", "01"), category("", "")],
      origins: [
        { key: "system", count: 6 },
        { key: "absent", count: 4 },
      ],
    })),
    quality: vi.fn(async () => quality()),
    sources: vi.fn(async () => sourcesReport()),
    records: vi.fn(async () => ({
      asOf: meta.asOf,
      total: 30,
      changedAfter: 2,
      items: [
        {
          offerId: "o1",
          name: "Offer one",
          sourceName: "Source a",
          supplierName: "",
          okpd2Code: "01.11.1",
          price: 84.5,
          currency: "RUB",
          url: "https://example.org/1",
          lastSeenAt: "2026-10-01T09:00:00Z",
        },
        {
          offerId: "o2",
          name: "Offer two",
          sourceName: "Source a",
          supplierName: "Alpha",
          okpd2Code: "",
          currency: "",
          url: "https://example.org/2",
          lastSeenAt: "2026-10-01T09:00:00Z",
        },
      ],
    })),
    ...overrides,
  }
}

const routes = [
  {
    path: "/analytics",
    Component: AnalyticsLayout,
    children: [
      { index: true, Component: OverviewPage },
      { path: "categories/:code?", Component: CategoriesPage },
      { path: "quality", Component: QualityPage },
      { path: "sources", Component: SourcesPage },
      { path: "records", Component: RecordsPage },
    ],
  },
]

export function renderAnalytics(
  path: string,
  gateway: AnalyticsGateway,
  locale: "en" | "ru" = "en",
) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const user = userEvent.setup()
  const result = render(
    <LocaleProvider initialLocale={locale}>
      <QueryClientProvider client={createQueryClient()}>
        <ToastProvider>
          <AnalyticsGatewayProvider gateway={gateway}>
            <RouterProvider router={router} />
          </AnalyticsGatewayProvider>
        </ToastProvider>
      </QueryClientProvider>
    </LocaleProvider>,
  )
  return { ...result, user, router }
}
