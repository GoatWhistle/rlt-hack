import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import type { Page } from "@playwright/test"

type Payload = Record<string, unknown>

const search = JSON.parse(
  readFileSync(
    resolve(process.cwd(), "..", "contracts", "search/response.example.json"),
    "utf8",
  ),
) as Payload

export async function installApiFixture(page: Page) {
  let uploaded = false
  const lots = [
    "test_paper",
    "test_workwear",
    "test_furniture",
    "test_cable",
    "test_cleaning",
  ].map((id) => ({
    id,
    title: id,
    subject: null,
    customerInn: null,
    publishDate: null,
    startPrice: null,
    status: "ready",
    products: (search.items as Payload[]).length,
    candidates: (search.candidates as Payload[]).length,
    searchId: `search-${id}`,
  }))
  const summary = {
    id: "test-upload",
    fileName: "notices-sample.csv",
    createdAt: "2026-10-01T10:00:00Z",
    total: lots.length,
    processed: lots.length,
    counts: { ready: lots.length, needsCheck: 0, noCandidates: 0, failed: 0 },
    rejected: 0,
  }
  const result = (lot: (typeof lots)[number]) => ({
    lot,
    search: {
      ...search,
      searchId: lot.searchId,
      query: { ...(search.query as Payload), text: lot.title, origin: "upload" },
    },
  })
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const request = route.request()
      const path = new URL(request.url()).pathname
      let payload: unknown
      if (path === "/api/uploads") {
        if (request.method() === "POST") {
          uploaded = true
          payload = summary
        } else payload = { uploads: uploaded ? [summary] : [] }
      } else if (path.endsWith("/results")) {
        const selected = request.postDataJSON().lotIds as string[]
        payload = { results: lots.filter((lot) => selected.includes(lot.id)).map(result) }
      } else if (path.includes("/lots/")) {
        const lot = lots.find((item) => path.endsWith(`/${item.id}`))
        if (!lot) return route.fulfill({ status: 404, json: { code: "notFound" } })
        payload = { ...result(lot), upload: summary }
      } else payload = { ...summary, lots, issues: [] }
      await route.fulfill({ json: payload })
    },
  )
}
