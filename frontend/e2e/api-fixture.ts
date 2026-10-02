import type { Page, Request } from "@playwright/test"
import { checkNotices } from "../src/entities/notice/check"
import { recommendationFixture } from "../tests/entities/recommendation/fixture"

export async function installApiFixture(page: Page) {
  let uploaded = false
  let lots = [
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
    products: recommendationFixture.products.length,
    candidates: recommendationFixture.companies.length,
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
    recommendation: {
      ...recommendationFixture,
      fileName: summary.fileName,
      requestTitle: lot.title,
      lotLabel: lot.id,
    },
  })
  function acceptTextSearch(request: Request) {
    const body = request.postData() ?? ""
    if (body.includes('filename="search.csv"')) {
      const csv = body.split("\r\n\r\n")[1]?.split("\r\n--")[0] ?? ""
      const parsed = checkNotices(csv, "search.csv")
      const first = lots[0]
      if (!parsed.ok || !parsed.notices[0] || !first)
        throw new Error("invalid search fixture input")
      lots = [{ ...first, id: "query", title: parsed.notices[0].title }]
      Object.assign(summary, {
        fileName: "search.csv",
        total: 1,
        processed: 1,
        counts: { ready: 1, needsCheck: 0, noCandidates: 0, failed: 0 },
      })
    }
  }
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const request = route.request()
      const path = new URL(request.url()).pathname
      let payload: unknown
      if (path === "/api/uploads") {
        if (request.method() === "POST") {
          acceptTextSearch(request)
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
