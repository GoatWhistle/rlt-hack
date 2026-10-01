import { afterEach, describe, expect, it, vi } from "vitest"
import { prefersReducedMotion, SETTLE_MS, settleDelay } from "@/shared/motion/settle-delay"

afterEach(() => {
  vi.unstubAllGlobals()
  Reflect.deleteProperty(window, "matchMedia")
})

function stubMotion(reduce: boolean) {
  Object.assign(window, { matchMedia: vi.fn(() => ({ matches: reduce })) })
}

describe("settleDelay", () => {
  it("waits for the indicator to settle when motion is allowed", () => {
    stubMotion(false)
    expect(prefersReducedMotion()).toBe(false)
    expect(settleDelay()).toBe(SETTLE_MS)
  })

  it("closes at once for people who reduce motion", () => {
    stubMotion(true)
    expect(settleDelay()).toBe(0)
  })

  it("treats a browser without matchMedia as allowing motion", () => {
    expect(prefersReducedMotion()).toBe(false)
  })
})
