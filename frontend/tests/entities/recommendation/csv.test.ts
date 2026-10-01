import { describe, expect, it } from "vitest"
import { CSV_BOM, csvFileName, toCsv } from "@/entities/recommendation/csv"
import { recommendationFixture } from "./fixture"

describe("toCsv", () => {
  it("writes one row per company with escaped cells", () => {
    const csv = toCsv(recommendationFixture, [
      { header: "Rank", value: (_, rank) => rank },
      { header: "Name; full", value: (company) => company.name },
      { header: "Quote", value: () => 'say "hi"' },
    ])
    const lines = csv.slice(CSV_BOM.length).trimEnd().split("\r\n")
    expect(csv.startsWith(CSV_BOM)).toBe(true)
    expect(lines).toEqual([
      'Rank;"Name; full";Quote',
      '1;North Foods;"say ""hi"""',
      expect.stringMatching(/^2;South Trade House/),
      '3;West Trade;"say ""hi"""',
    ])
  })
})

describe("csvFileName", () => {
  it("names the export after the uploaded file", () => {
    expect(csvFileName(recommendationFixture)).toBe("lot-suppliers.csv")
    expect(csvFileName({ ...recommendationFixture, fileName: ".xlsx" })).toBe(
      "recommendation-suppliers.csv",
    )
  })
})
