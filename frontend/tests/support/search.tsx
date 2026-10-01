import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, RouterProvider } from "react-router"
import { vi } from "vitest"
import { createDemoSearchGateway } from "@/entities/search/demo/gateway"
import { createSearchStore } from "@/entities/search/demo/store"
import type { SearchGateway } from "@/entities/search/gateway"
import { SearchGatewayProvider } from "@/entities/search/gateway-context"
import type { SearchResult } from "@/entities/search/model"
import { parseSearchResult } from "@/entities/search/parse"
import { createDemoSupplierGateway } from "@/entities/supplier/demo/gateway"
import type { SupplierGateway } from "@/entities/supplier/gateway"
import { SupplierGatewayProvider } from "@/entities/supplier/gateway-context"
import { SearchPage, SearchResultPage } from "@/pages/search"
import { createQueryClient } from "@/shared/api/query-client"
import type { Locale } from "@/shared/i18n/locale"
import { LocaleProvider } from "@/shared/i18n/locale-provider"
import { createJsonStorage } from "@/shared/storage/local-json"
import { ToastProvider } from "@/shared/ui/toast"

const CONTRACTS = resolve(process.cwd(), "..", "contracts")

export function contract(path: string): unknown {
  return JSON.parse(readFileSync(resolve(CONTRACTS, path), "utf8"))
}

export function contractResult(): SearchResult {
  return parseSearchResult(contract("search/response.example.json"))
}

export function instant(): Promise<void> {
  return Promise.resolve()
}

export function demoSearch(locale: () => Locale = () => "en"): SearchGateway {
  return createDemoSearchGateway({
    store: createSearchStore(createJsonStorage()),
    wait: instant,
    locale,
  })
}

export function stubSearch(overrides: Partial<SearchGateway> = {}): SearchGateway {
  return {
    demo: false,
    search: vi.fn(async () => contractResult()),
    get: vi.fn(async () => contractResult()),
    recent: vi.fn(async () => []),
    ...overrides,
  }
}

export type SearchPageOptions = {
  readonly gateway?: SearchGateway
  readonly suppliers?: SupplierGateway
  readonly locale?: Locale
}

export function renderSearch(path: string, options: SearchPageOptions = {}) {
  const routes = [
    { path: "/search", Component: SearchPage },
    { path: "/search/:searchId", Component: SearchResultPage },
  ]
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const gateway = options.gateway ?? stubSearch()
  const suppliers = options.suppliers ?? createDemoSupplierGateway({ locale: () => "en" })
  const user = userEvent.setup()
  const result = render(
    <LocaleProvider initialLocale={options.locale ?? "en"}>
      <QueryClientProvider client={createQueryClient()}>
        <ToastProvider>
          <SearchGatewayProvider gateway={gateway}>
            <SupplierGatewayProvider gateway={suppliers}>
              <RouterProvider router={router} />
            </SupplierGatewayProvider>
          </SearchGatewayProvider>
        </ToastProvider>
      </QueryClientProvider>
    </LocaleProvider>,
  )
  return { ...result, user, router, gateway }
}
