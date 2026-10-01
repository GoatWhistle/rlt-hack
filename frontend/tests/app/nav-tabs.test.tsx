import { act, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { en } from "@tests/support/dictionaries"
import { createMemoryRouter, RouterProvider } from "react-router"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { NavTabs } from "@/app/nav-tabs"
import { measureActive } from "@/app/nav-tabs/use-indicator"
import { LocaleProvider } from "@/shared/i18n/locale-provider"

const observers: ResizeObserverCallback[] = []

class ResizeObserverStub {
  readonly callback: ResizeObserverCallback
  constructor(callback: ResizeObserverCallback) {
    this.callback = callback
    observers.push(callback)
  }
  observe() {}
  unobserve() {}
  disconnect() {}
}

let tabWidth = 80

function stubLayout() {
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockImplementation(function width(
    this: HTMLElement,
  ) {
    return this.tagName === "A" ? tabWidth : 0
  })
  vi.spyOn(HTMLElement.prototype, "offsetLeft", "get").mockImplementation(function left(
    this: HTMLElement,
  ) {
    return this.getAttribute("href") === "/lots" ? 100 : 0
  })
}

function renderTabs(path: string) {
  const routes = [{ path: "*", Component: NavTabs }]
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <LocaleProvider initialLocale="en">
      <RouterProvider router={router} />
    </LocaleProvider>,
  )
  return { router, user: userEvent.setup() }
}

function indicator() {
  return screen.getByRole("navigation").querySelector<HTMLElement>("span[aria-hidden='true']")
}

describe("the navigation tabs", () => {
  beforeEach(() => {
    tabWidth = 80
    observers.length = 0
    vi.stubGlobal("ResizeObserver", ResizeObserverStub)
    stubLayout()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it("marks the current tab and slides the indicator under it", async () => {
    const { user } = renderTabs("/uploads")
    const uploads = screen.getByRole("link", { name: en("nav.uploads") })
    expect(uploads).toHaveAttribute("aria-current", "page")
    const nav = screen.getByRole("navigation", { name: en("app.mainNavigation") })
    expect(nav.style.getPropertyValue("--indicator-x")).toBe("0px")
    expect(nav.style.getPropertyValue("--indicator-scale")).toBe("80")
    expect(indicator()).not.toBeNull()

    await user.click(screen.getByRole("link", { name: en("nav.lots") }))
    expect(screen.getByRole("link", { name: en("nav.lots") })).toHaveAttribute(
      "aria-current",
      "page",
    )
    expect(uploads).not.toHaveAttribute("aria-current")
    expect(nav.style.getPropertyValue("--indicator-x")).toBe("100px")
  })

  it("treats every page inside an upload as the purchases tab", () => {
    renderTabs("/uploads/u1/lots/7")
    expect(screen.getByRole("link", { name: en("nav.lots") })).toHaveAttribute(
      "aria-current",
      "page",
    )
  })

  it("marks the search tab on the search page and on a result", async () => {
    const { router } = renderTabs("/search")
    const search = screen.getByRole("link", { name: en("nav.search") })
    expect(search).toHaveAttribute("aria-current", "page")
    expect(search).toHaveAttribute("href", "/search")
    expect(indicator()).not.toBeNull()
    await act(() => router.navigate("/search/abc"))
    expect(screen.getByRole("link", { name: en("nav.search") })).toHaveAttribute(
      "aria-current",
      "page",
    )
    expect(screen.getAllByRole("link")).toHaveLength(3)
  })

  it("follows the tab when its width changes", () => {
    renderTabs("/uploads")
    const nav = screen.getByRole("navigation")
    tabWidth = 120
    act(() => {
      for (const callback of observers) callback([], {} as ResizeObserver)
    })
    expect(nav.style.getPropertyValue("--indicator-scale")).toBe("120")
  })

  it("hides the indicator when no tab matches the page", () => {
    renderTabs("/missing")
    expect(indicator()).toBeNull()
    expect(screen.getByRole("navigation").querySelector("[aria-current]")).toBeNull()
  })

  it("turns the slide on only after the first placement and the font swap", async () => {
    let fontsLoaded: () => void = () => {}
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      callback(0)
      return 1
    })
    Object.defineProperty(document, "fonts", {
      configurable: true,
      value: { ready: new Promise<void>((resolve) => (fontsLoaded = resolve)) },
    })
    renderTabs("/uploads")
    const nav = screen.getByRole("navigation")
    expect(nav).toHaveAttribute("data-indicator", "ready")
    tabWidth = 96
    await act(async () => fontsLoaded())
    expect(nav.style.getPropertyValue("--indicator-scale")).toBe("96")
    expect(nav).toHaveAttribute("data-indicator", "ready")
    Reflect.deleteProperty(document, "fonts")
  })

  it("measures the tab without its padding", () => {
    const root = document.createElement("nav")
    const tab = document.createElement("a")
    tab.setAttribute("aria-current", "page")
    tab.style.paddingInlineStart = "12px"
    tab.style.paddingInlineEnd = "12px"
    root.append(tab)
    expect(measureActive(root)).toEqual({ x: 12, width: 56 })
  })

  it("does not measure a tab that is not laid out", () => {
    const root = document.createElement("nav")
    expect(measureActive(root)).toBeNull()
  })
})
