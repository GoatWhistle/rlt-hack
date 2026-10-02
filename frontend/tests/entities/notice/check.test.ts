import { describe, expect, it } from "vitest"
import { checkNotices, parsePrice } from "@/entities/notice/check"
import { detectDelimiter, readCsv } from "@/entities/notice/csv-reader"
import { decodeFile } from "@/entities/notice/decode"

const HEADER =
  '"publish_date";"lot_id";"start_price";"procedure_name";"subject";"customer_inn";"note"'

function file(...rows: string[]): string {
  return `﻿${[HEADER, ...rows].join("\r\n")}\r\n`
}

describe("readCsv", () => {
  it("handles quotes, escaped quotes, line breaks inside cells and blank lines", () => {
    const records = readCsv('a;b\n"x;1";"say ""hi"""\n\n"multi\nline";z\nlast;')
    expect(records).toEqual([
      { line: 1, cells: ["a", "b"] },
      { line: 2, cells: ["x;1", 'say "hi"'] },
      { line: 4, cells: ["multi\nline", "z"] },
      { line: 6, cells: ["last", ""] },
    ])
  })

  it("guesses the separator from the header", () => {
    expect(detectDelimiter("a,b,c\n1;2")).toBe(",")
    expect(detectDelimiter("a\tb")).toBe("\t")
    expect(detectDelimiter("single")).toBe(";")
  })
})

describe("parsePrice", () => {
  it("reads spaced and comma decimals, rejects garbage", () => {
    expect(parsePrice("1 234,50")).toBe(1234.5)
    expect(parsePrice("")).toBeUndefined()
    expect(parsePrice("abc")).toBeNull()
    expect(parsePrice("-5")).toBeNull()
  })
})

describe("checkNotices", () => {
  it("keeps valid rows, lists errors by file row and recognises columns", () => {
    const check = checkNotices(
      file(
        '2025-01-02;100;1000.00;"Food";"Food";"7800000001";x',
        "2025-01-03;101;;Paper;Office paper;;",
        "2025-01-04;100;10;Duplicate;;;",
        "2025-13-45;;abc;;;;",
        "2025-01-05;bad id;1;Name;;;",
        "2025-01-06;102;1;Name;;;;extra",
        "nope;103;1;Name;;;",
      ),
      "notices.csv",
    )
    if (!check.ok) throw new Error("expected an accepted file")
    expect(check.total).toBe(7)
    expect(check.notices).toEqual([
      {
        lotId: "100",
        title: "Food",
        startPrice: 1000,
        customerInn: "7800000001",
        publishDate: "2025-01-02",
      },
      { lotId: "101", title: "Paper", subject: "Office paper", publishDate: "2025-01-03" },
    ])
    expect(check.issues).toEqual([
      { row: 4, code: "duplicateLot", value: "100" },
      { row: 5, code: "missingLotId" },
      { row: 5, code: "missingTitle" },
      { row: 5, code: "badPrice", value: "abc" },
      { row: 5, code: "badDate", value: "2025-13-45" },
      { row: 6, code: "badLotId", value: "bad id" },
      { row: 7, code: "columnCount" },
      { row: 8, code: "badDate", value: "nope" },
    ])
    expect(check.columns.map((column) => column.known)).toEqual([
      true,
      true,
      true,
      true,
      true,
      true,
      false,
    ])
    expect(check.preview).toHaveLength(5)
    expect(check.preview[0]).toEqual({
      line: 2,
      cells: ["2025-01-02", "100", "1000.00", "Food", "Food", "7800000001", "x"],
    })
  })

  it("rejects empty files and missing columns", () => {
    expect(checkNotices("", "a.csv")).toMatchObject({ problem: "empty" })
    expect(checkNotices(file(), "a.csv")).toMatchObject({ problem: "empty" })
    expect(checkNotices("lot_id;price\n1;2", "a.csv")).toEqual({
      ok: false,
      fileName: "a.csv",
      problem: "missingColumns",
      missing: ["procedure_name"],
    })
  })

  it("accepts more than twenty rows", () => {
    const rows = Array.from({ length: 25 }, (_, index) => `2025-01-01;${index};1;Item;;;`)
    const check = checkNotices(file(...rows), "many.csv")
    expect(check.ok && check.total).toBe(25)
  })

  it("falls back to the subject when the name is empty", () => {
    const check = checkNotices(file("2025-01-01;1;;;Subject only;;"), "a.csv")
    expect(check.ok && check.notices[0]?.title).toBe("Subject only")
  })
})

describe("decodeFile", () => {
  it("reads utf-8 and falls back to windows-1251", async () => {
    expect(await decodeFile(new Blob(["lot_id"]))).toBe("lot_id")
    const cp1251 = new Uint8Array([0xcf, 0xf0, 0xe8, 0xe2, 0xe5, 0xf2])
    expect(await decodeFile(new Blob([cp1251]))).toBe("Привет")
  })
})
