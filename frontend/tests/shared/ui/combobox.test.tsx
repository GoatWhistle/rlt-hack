import { describe, expect, it } from "vitest"
import type { ComboboxGroup } from "@/shared/ui/combobox"
import { nextActive, PAGE_STEP, revealOption } from "@/shared/ui/combobox/navigation"
import { fold, search, sectionsFor } from "@/shared/ui/combobox/search"
import { place, shiftFor, sideFor } from "@/shared/ui/combobox/use-placement"

const GROUPS: readonly ComboboxGroup[] = [
  { key: "none", options: [{ key: "none", value: "", label: "Anywhere" }] },
  {
    key: "towns",
    label: "Towns",
    options: [
      { key: "t-1", value: "1", label: "Ёлкино", detail: "Лесной край" },
      { key: "t-2", value: "2", label: "Bay-Town", keywords: ["harbour"] },
    ],
  },
  {
    key: "areas",
    label: "Areas",
    options: [
      { key: "a-1", value: "1", label: "Северный край" },
      { key: "a-3", value: "3", label: "Upper Elkino" },
    ],
  },
]

const labels = (query: string) =>
  search(GROUPS, query, "ru-RU").map((item) => item.option.label)

describe("combobox search", () => {
  it("folds case, ё and dashes without changing the length", () => {
    expect(fold("Ёлки-Палки", "ru-RU")).toBe("елки палки")
    expect(fold("Ёлки-Палки", "ru-RU")).toHaveLength("Ёлки-Палки".length)
  })

  it("ranks a name start over a word start and a keyword over a detail", () => {
    expect(labels("елк")).toEqual(["Ёлкино"])
    expect(labels("elk")).toEqual(["Upper Elkino"])
    expect(labels("bay town")).toEqual(["Bay-Town"])
    expect(labels("harb")).toEqual(["Bay-Town"])
    expect(labels("север")).toEqual(["Северный край"])
    expect(labels("лесн")).toEqual(["Ёлкино"])
    expect(labels("own")).toEqual(["Bay-Town"])
    expect(labels("zzz")).toEqual([])
  })

  it("marks the matched part of the name and the detail", () => {
    const [town] = search(GROUPS, "лкин", "ru-RU")
    expect(town?.label).toEqual([1, 5])
    const [forest] = search(GROUPS, "лесн", "ru-RU")
    expect(forest?.detail).toEqual([0, 4])
  })

  it("keeps the groups for an empty query and flattens the results otherwise", () => {
    expect(sectionsFor(GROUPS, "  ", "en").map((section) => section.label)).toEqual([
      undefined,
      "Towns",
      "Areas",
    ])
    expect(sectionsFor(GROUPS, "up", "en")).toHaveLength(1)
    expect(sectionsFor(GROUPS, "nothing", "en")).toEqual([])
  })
})

describe("combobox navigation", () => {
  it("wraps arrows, jumps to the ends and pages without wrapping", () => {
    expect(nextActive("ArrowDown", -1, 5)).toBe(0)
    expect(nextActive("ArrowDown", 4, 5)).toBe(0)
    expect(nextActive("ArrowUp", -1, 5)).toBe(4)
    expect(nextActive("ArrowUp", 0, 5)).toBe(4)
    expect(nextActive("Home", 3, 5)).toBe(0)
    expect(nextActive("End", 0, 5)).toBe(4)
    expect(nextActive("PageDown", 0, 20)).toBe(PAGE_STEP)
    expect(nextActive("PageDown", 18, 20)).toBe(19)
    expect(nextActive("PageUp", 3, 20)).toBe(0)
    expect(nextActive("x", 0, 5)).toBeNull()
    expect(nextActive("ArrowDown", 0, 0)).toBeNull()
  })

  it("scrolls the list just enough to show the option below a sticky heading", () => {
    const list = document.createElement("div")
    const group = document.createElement("div")
    const heading = document.createElement("div")
    const option = document.createElement("div")
    heading.dataset.heading = ""
    group.append(heading, option)
    list.append(group)
    Object.defineProperties(list, { clientHeight: { value: 100 } })
    Object.defineProperties(heading, { offsetHeight: { value: 20 } })
    Object.defineProperties(option, {
      offsetTop: { value: 300, configurable: true },
      offsetHeight: { value: 40 },
    })
    revealOption(list, option, false)
    expect(list.scrollTop).toBe(240)
    Object.defineProperty(option, "offsetTop", { value: 230 })
    revealOption(list, option, false)
    expect(list.scrollTop).toBe(210)
    revealOption(list, option, true)
    expect(list.scrollTop).toBe(200)
    revealOption(null, option, true)
  })
})

describe("combobox placement", () => {
  it("opens below unless the room above is clearly larger", () => {
    expect(sideFor(400, 100, 240)).toBe("bottom")
    expect(sideFor(200, 100, 240)).toBe("bottom")
    expect(sideFor(200, 500, 240)).toBe("top")
  })

  it("shifts the panel left only as far as the viewport needs", () => {
    expect(shiftFor(10, 300, 1000)).toBe(0)
    expect(shiftFor(800, 300, 1000)).toBe(-108)
    expect(shiftFor(20, 500, 300)).toBe(-12)
  })

  it("writes the room and the side on the panel", () => {
    const panel = document.createElement("div")
    const trigger = document.createElement("button")
    trigger.getBoundingClientRect = () => ({ top: 600, bottom: 640, left: 10 }) as DOMRect
    Object.defineProperty(window, "innerHeight", { value: 800, configurable: true })
    expect(place(panel, trigger)).toBe("top")
    expect(panel.dataset.side).toBe("top")
    expect(panel.style.getPropertyValue("--combobox-room")).toBe("584px")
    Object.assign(window, { matchMedia: () => ({ matches: true }) })
    expect(place(panel, trigger)).toBe("sheet")
    Object.assign(window, { matchMedia: undefined })
  })
})
