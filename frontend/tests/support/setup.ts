import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
import { afterEach, beforeAll, vi } from "vitest"
import { i18n, initI18n } from "@/shared/i18n/i18n"

function blockedFetch(input: RequestInfo | URL): Promise<Response> {
  return Promise.reject(
    new Error(`tests do not reach the network: fetch ${String(input)} was refused`),
  )
}

beforeAll(() => {
  globalThis.fetch = vi.fn(blockedFetch)
  initI18n("en")
})

afterEach(async () => {
  cleanup()
  vi.useRealTimers()
  localStorage.clear()
  document.documentElement.removeAttribute("lang")
  await i18n.changeLanguage("en")
})
