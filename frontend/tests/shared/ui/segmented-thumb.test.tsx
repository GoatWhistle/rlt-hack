import { render } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { SegmentedControl } from "@/shared/ui/segmented-control"

const OPTIONS = [
  { value: "all", label: "All" },
  { value: "ready", label: "Ready" },
]

function stubLayout() {
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockImplementation(function width(
    this: HTMLElement,
  ) {
    return this.tagName === "LABEL" ? (this.textContent === "All" ? 40 : 80) : 0
  })
  vi.spyOn(HTMLElement.prototype, "offsetLeft", "get").mockImplementation(function left(
    this: HTMLElement,
  ) {
    return this.textContent === "Ready" ? 48 : 4
  })
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(44)
}

function renderControl(value: string) {
  return (
    <SegmentedControl legend="Filter" value={value} onChange={() => {}} options={OPTIONS} />
  )
}

describe("the segmented control thumb", () => {
  afterEach(() => vi.restoreAllMocks())

  it("sits under the checked option and slides to the next one", () => {
    stubLayout()
    const animate = vi.fn()
    Object.defineProperty(HTMLElement.prototype, "animate", {
      configurable: true,
      value: animate,
    })
    const { container, rerender } = render(renderControl("all"))
    const group = container.querySelector("fieldset") as HTMLElement
    expect(group).toHaveAttribute("data-thumb", "placed")
    expect(group.style.getPropertyValue("--thumb-x")).toBe("4px")
    expect(group.style.getPropertyValue("--thumb-width")).toBe("40px")
    expect(animate).not.toHaveBeenCalled()
    rerender(renderControl("ready"))
    expect(group.style.getPropertyValue("--thumb-x")).toBe("48px")
    expect(animate).toHaveBeenCalledTimes(1)
    expect(animate.mock.calls[0]?.[0][0].transform).toBe("translate(-44px, 0px) scale(0.5, 1)")
    Reflect.deleteProperty(HTMLElement.prototype, "animate")
  })

  it("hides the thumb when the options are not laid out", () => {
    const { container } = render(renderControl("all"))
    expect(container.querySelector("fieldset")).toHaveAttribute("data-thumb", "hidden")
  })
})
