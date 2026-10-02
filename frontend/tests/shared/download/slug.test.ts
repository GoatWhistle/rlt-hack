import { describe, expect, it } from "vitest"
import { searchFileName } from "@/features/export-results/search-csv"
import { slugOf } from "@/shared/download/slug"

describe("slugOf", () => {
  it("transliterates the first words of a Russian query", () => {
    expect(slugOf("Крупа гречневая ядрица 500 кг; рис")).toBe("krupa-grechnevaya-yadritsa")
    expect(slugOf("Щётка, мыло хозяйственное", 2)).toBe("shchetka-mylo")
  })

  it("keeps latin words and digits and drops signs", () => {
    expect(slugOf("Paper A4 — 80 g/m²")).toBe("paper-a4-80")
    expect(slugOf("ъ ь !!!")).toBe("")
  })

  it("names the search export after the query and the day", () => {
    expect(searchFileName("Перчатки нитриловые M", "2026-10-02T08:00:00Z")).toBe(
      "lotive-perchatki-nitrilovye-m-2026-10-02.csv",
    )
    expect(searchFileName("!!!", "2026-10-02T08:00:00Z")).toBe("lotive-search-2026-10-02.csv")
  })
})
