import { contract } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import { createHttpSearchGateway, SEARCHES_PATH } from "@/entities/search/http"
import { createHttpClient } from "@/shared/api/http-client"

function respond(body: unknown, status = 200) {
  return vi.fn(
    async (_url: RequestInfo | URL, _init?: RequestInit) =>
      new Response(JSON.stringify(body), { status }),
  )
}

describe("the http search gateway", () => {
  it("posts the query and reads the result", async () => {
    const fetcher = respond(contract("search/response.example.json"))
    const gateway = createHttpSearchGateway(createHttpClient({ baseUrl: "/api", fetcher }))
    const request = contract("search/request.example.json") as { text: string }
    const result = await gateway.search(request)
    expect(result.candidates).toHaveLength(2)
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe(`/api${SEARCHES_PATH}`)
    expect(init.method).toBe("POST")
    expect(JSON.parse(String(init.body))).toEqual(request)
  })

  it("reads one search and the recent ones", async () => {
    const one = respond(contract("search/response.example.json"))
    await createHttpSearchGateway(createHttpClient({ baseUrl: "/api", fetcher: one })).get(
      "a/b",
    )
    expect(one.mock.calls[0]?.[0]).toBe("/api/searches/a%2Fb")
    const recent = respond(contract("search/recent.example.json"))
    const list = await createHttpSearchGateway(
      createHttpClient({ baseUrl: "/api", fetcher: recent }),
    ).recent(8)
    expect(list).toHaveLength(1)
    expect(recent.mock.calls[0]?.[0]).toBe("/api/searches?limit=8")
  })

  it("turns an error body into a coded error", async () => {
    const fetcher = respond(contract("search/error.example.json"), 422)
    const gateway = createHttpSearchGateway(createHttpClient({ baseUrl: "/api", fetcher }))
    await expect(gateway.search({ text: "x" })).rejects.toMatchObject({
      status: 422,
      code: "query_too_long",
    })
  })
})
