import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, RouterProvider } from "react-router"
import { vi } from "vitest"
import type { SearchGateway } from "@/entities/search/gateway"
import { SearchGatewayProvider } from "@/entities/search/gateway-context"
import type { SearchResult } from "@/entities/search/model"
import { parseSearchResult } from "@/entities/search/parse"
import type { SupplierGateway } from "@/entities/supplier/gateway"
import { SupplierGatewayProvider } from "@/entities/supplier/gateway-context"
import { parseSupplierProfile } from "@/entities/supplier/parse"
import type { UploadGateway } from "@/entities/upload/gateway"
import { UploadGatewayProvider } from "@/entities/upload/gateway-context"
import { SearchPage, SearchResultPage } from "@/pages/search"
import { createQueryClient } from "@/shared/api/query-client"
import type { Locale } from "@/shared/i18n/locale"
import { LocaleProvider } from "@/shared/i18n/locale-provider"
import { ToastProvider } from "@/shared/ui/toast"
import { stubGateway } from "./gateway"

const CONTRACTS = resolve(process.cwd(), "..", "contracts")

export function contract(path: string): unknown {
  return JSON.parse(readFileSync(resolve(CONTRACTS, path), "utf8"))
}

type Payload = Record<string, unknown>

export function contractResult(
  change: (payload: Payload) => Payload = (payload) => payload,
): SearchResult {
  return parseSearchResult(change(contract("search/response.example.json") as Payload))
}

export function stubSuppliers(overrides: Partial<SupplierGateway> = {}): SupplierGateway {
  return {
    profile: vi.fn(async () => parseSupplierProfile(contract("supplier/profile.example.json"))),
    ...overrides,
  }
}

export function stubSearch(overrides: Partial<SearchGateway> = {}): SearchGateway {
  const recent = overrides.recent ?? vi.fn(async () => [])
  return {
    search: vi.fn(async () => contractResult()),
    get: vi.fn(async () => contractResult()),
    history: vi.fn(async (limit: number) => {
      const searches = await recent(limit)
      return { searches, hasMore: false, total: searches.length }
    }),
    ...overrides,
    recent,
  }
}

export type SearchPageOptions = {
  readonly gateway?: SearchGateway
  readonly suppliers?: SupplierGateway
  readonly uploads?: UploadGateway
  readonly locale?: Locale
}

export function renderSearch(path: string, options: SearchPageOptions = {}) {
  const routes = [
    { path: "/search", Component: SearchPage },
    { path: "/search/:searchId", Component: SearchResultPage },
    { path: "/uploads/:uploadId/lots/:lotId", element: <div /> },
    { path: "/uploads/:uploadId", element: <div /> },
    { path: "/history", element: <div /> },
  ]
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const gateway = options.gateway ?? stubSearch()
  const suppliers = options.suppliers ?? stubSuppliers()
  const uploads = options.uploads ?? stubGateway()
  const user = userEvent.setup()
  const result = render(
    <LocaleProvider initialLocale={options.locale ?? "en"}>
      <QueryClientProvider client={createQueryClient()}>
        <ToastProvider>
          <SearchGatewayProvider gateway={gateway}>
            <UploadGatewayProvider gateway={uploads}>
              <SupplierGatewayProvider gateway={suppliers}>
                <RouterProvider router={router} />
              </SupplierGatewayProvider>
            </UploadGatewayProvider>
          </SearchGatewayProvider>
        </ToastProvider>
      </QueryClientProvider>
    </LocaleProvider>,
  )
  return { ...result, user, router, gateway, uploads }
}
