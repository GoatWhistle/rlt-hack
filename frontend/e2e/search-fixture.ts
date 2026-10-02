import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import type { Page } from "@playwright/test"

type Payload = Record<string, unknown>

const CONTRACTS = resolve(process.cwd(), "..", "contracts")
const UNREADABLE = /^[\d\s!?.,;:-]*$/
const NOTHING_FOUND = /tractor/i
const INFERRED = /office/i
const TRUNCATED = /many items/i
const ARCHIVED = /archived/i

function contract(path: string): Payload {
  return JSON.parse(readFileSync(resolve(CONTRACTS, path), "utf8")) as Payload
}

function warnings(text: string): Payload[] {
  return [
    ...(INFERRED.test(text) ? [{ code: "itemsInferred", subject: "" }] : []),
    ...(TRUNCATED.test(text) ? [{ code: "itemsTruncated", subject: "" }] : []),
  ]
}

function answer(text: string, searchId: string): Payload {
  const { offers, ...base } = contract("search/response.example.json")
  const items = base.items as Payload[]
  return {
    ...base,
    searchId,
    query: { ...(base.query as Payload), text },
    items: INFERRED.test(text) ? items.map((item) => ({ ...item, origin: "inferred" })) : items,
    candidates: NOTHING_FOUND.test(text) ? [] : base.candidates,
    warnings: warnings(text),
    ...(ARCHIVED.test(text) ? {} : { offers }),
  }
}

function summary(search: Payload): Payload {
  const candidates = search.candidates as Payload[]
  return {
    searchId: search.searchId,
    text: (search.query as Payload).text,
    locale: "en",
    items: (search.items as Payload[]).length,
    candidates: candidates.length,
    recommended: candidates.filter((candidate) => candidate.status === "recommended").length,
    createdAt: search.createdAt,
  }
}

export async function installSearchFixture(page: Page) {
  const searches = new Map<string, Payload>()
  const profile = contract("supplier/profile.example.json")
  await page.route(
    (url) =>
      url.pathname.startsWith("/api/searches") || url.pathname.startsWith("/api/suppliers/"),
    async (route) => {
      const request = route.request()
      const path = new URL(request.url()).pathname
      if (path.startsWith("/api/suppliers/")) return route.fulfill({ json: profile })
      if (path === "/api/searches" && request.method() === "POST") {
        const text = String((request.postDataJSON() as Payload).text ?? "")
        if (UNREADABLE.test(text)) {
          return route.fulfill({ status: 422, json: { code: "query_not_understood" } })
        }
        const search = answer(text, `search-${searches.size + 1}`)
        searches.set(String(search.searchId), search)
        return route.fulfill({ json: search })
      }
      if (path === "/api/searches") {
        return route.fulfill({
          json: { searches: [...searches.values()].reverse().map(summary) },
        })
      }
      const search = searches.get(decodeURIComponent(path.split("/").at(-1) ?? ""))
      if (!search) return route.fulfill({ status: 404, json: { code: "search_not_found" } })
      return route.fulfill({ json: search })
    },
  )
}
