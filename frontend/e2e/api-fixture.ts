import type { Page } from "@playwright/test"
import { recommendationFixture } from "../tests/entities/recommendation/fixture"

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
    status: "ready",
    products: recommendationFixture.products.length,
    candidates: recommendationFixture.companies.length,
  }))
  const summary = {
    id: "test-upload",
    fileName: "notices-sample.csv",
    createdAt: "2026-10-01T10:00:00Z",
    total: lots.length,
    processed: lots.length,
    counts: { ready: lots.length, needsCheck: 0, noCandidates: 0 },
    rejected: 0,
    stored: true,
  }
  const result = (lot: (typeof lots)[number]) => ({
    lot,
    recommendation: {
      ...recommendationFixture,
      fileName: summary.fileName,
      requestTitle: lot.title,
      lotLabel: lot.id,
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
