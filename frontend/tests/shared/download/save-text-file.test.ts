import { afterEach, describe, expect, it, vi } from "vitest"
import { saveTextFile } from "@/shared/download/save-text-file"

afterEach(() => {
  vi.restoreAllMocks()
})

describe("saveTextFile", () => {
  it("downloads the text through a temporary link", async () => {
    const create = vi.fn((_: Blob) => "blob:file")
    const revoke = vi.fn()
    Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke })
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {})
    saveTextFile("a.csv", "x;y", "text/csv")
    const blob = create.mock.calls[0]?.[0]
    if (!blob) throw new Error("no blob was created")
    expect(await blob.text()).toBe("x;y")
    expect(blob.type).toBe("text/csv")
    expect(click).toHaveBeenCalledOnce()
    expect(revoke).toHaveBeenCalledWith("blob:file")
  })
})
