import { describe, expect, it } from "vitest"
import { intakeFile } from "@/features/file-intake/inspect"
import {
  ACCEPTED_FILES,
  extensionOf,
  kindOf,
  lotsOf,
  sendable,
  sizeOf,
  splitName,
} from "@/features/file-intake/model"

describe("file intake", () => {
  it("accepts the documented formats and recognises their kind", () => {
    expect(ACCEPTED_FILES).toBe(".csv,.xlsx,.xls,.pdf,.docx,.doc,.txt")
    expect(kindOf("Lots.CSV")).toBe("csv")
    expect(kindOf("table.xls")).toBe("sheet")
    expect(kindOf("terms.doc")).toBe("document")
    expect(kindOf("notes.txt")).toBe("text")
    expect(kindOf("photo.png")).toBeUndefined()
    expect(extensionOf(".hidden")).toBe("")
    expect(extensionOf("archive")).toBe("")
  })

  it("names sizes in bytes, kilobytes and megabytes", () => {
    expect(sizeOf(512)).toEqual({ unit: "b", value: 512 })
    expect(sizeOf(2048)).toEqual({ unit: "kb", value: 2 })
    expect(sizeOf(2.46 * 1024 * 1024)).toEqual({ unit: "mb", value: 2.5 })
  })

  it("keeps the extension and the end of a long name visible", () => {
    expect(splitName("zakupki-oktyabr-region-78.csv")).toEqual([
      "zakupki-oktyabr-reg",
      "ion-78.csv",
    ])
    expect(splitName("a.csv")).toEqual(["", "a.csv"])
    expect(splitName("README")).toEqual(["", "README"])
  })

  it("sends only a checked CSV with purchases", async () => {
    expect(sendable(null)).toBeNull()
    const later = await intakeFile(new File(["PK"], "sheet.xlsx"))
    expect(later).toMatchObject({ status: "later", kind: "sheet" })
    expect(sendable(later)).toBeNull()
    const checked = await intakeFile(new File(["lot_id;procedure_name\nA1;Paper"], "a.csv"))
    const upload = sendable(checked)
    expect(upload && lotsOf(upload)).toEqual(["A1"])
    expect(await intakeFile(new File([""], "empty.pdf"))).toMatchObject({
      status: "rejected",
      reason: "unreadable",
    })
    expect(await intakeFile(new File(["hello"], "notes.txt"))).toMatchObject({
      status: "later",
      kind: "text",
    })
  })
})
