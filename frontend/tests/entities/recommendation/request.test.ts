import { afterEach, describe, expect, it, vi } from "vitest"
import {
  DEMO_DELAY_MS,
  RECOMMENDATIONS_PATH,
  requestRecommendation,
} from "@/entities/recommendation/request"
import type { HttpClient } from "@/shared/api/http-client"
import { recommendationFixture } from "./fixture"

const file = new File(["data"], "lot.xlsx")

function clientReturning(payload: unknown): HttpClient {
  return {
    get: vi.fn(),
    post: vi.fn((_path, options) => Promise.resolve(options.parse(payload))),
  }
}

afterEach(() => {
  vi.useRealTimers()
})

describe("requestRecommendation", () => {
  it("serves the demo result under the uploaded file name", async () => {
    vi.useFakeTimers()
    const client = clientReturning(null)
    const pending = requestRecommendation(file, { client, demoMode: true })
    await vi.advanceTimersByTimeAsync(DEMO_DELAY_MS)
    const result = await pending
    expect(result.fileName).toBe("lot.xlsx")
    expect(result.companies.length).toBeGreaterThan(0)
    expect(client.post).not.toHaveBeenCalled()
  })

  it("posts the file to the api and parses the answer", async () => {
    const client = clientReturning(recommendationFixture)
    await expect(requestRecommendation(file, { client, demoMode: false })).resolves.toEqual(
      recommendationFixture,
    )
    const [path, options] = vi.mocked(client.post).mock.calls[0] ?? []
    expect(path).toBe(RECOMMENDATIONS_PATH)
    const body = options?.body
    expect(body).toBeInstanceOf(FormData)
    expect(body instanceof FormData && body.get("file")).toBeInstanceOf(File)
  })
})
