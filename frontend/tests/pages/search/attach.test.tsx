import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { stubGateway, uploadSummary } from "@tests/support/gateway"
import { renderSearch } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import type { UploadGateway } from "@/entities/upload/gateway"

const CSV = [
  "lot_id;procedure_name;start_price",
  "L1;Food;100",
  "L2;Paper;bad",
  "L3;Ink;5",
].join("\n")

function file(content: BlobPart, name: string, type = "") {
  return new File([content], name, { type })
}

function picker(): HTMLInputElement {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]')
  if (!input) throw new Error("no file input")
  return input
}

function field() {
  return document.querySelector<HTMLElement>("[data-part='query-text']")?.parentElement
}

function dragEvent(type: string, files: readonly File[] = []) {
  const event = new Event(type, { bubbles: true, cancelable: true })
  Object.defineProperty(event, "dataTransfer", {
    value: { types: ["Files"], files, dropEffect: "none" },
  })
  return event
}

function find() {
  return screen.getByRole("button", { name: en("box.submit", "search") })
}

function open(uploads: UploadGateway = stubGateway()) {
  const view = renderSearch("/search", { uploads })
  const click = vi.spyOn(picker(), "click")
  return { ...view, click }
}

describe("attaching a file to the search", () => {
  it("opens the system picker, checks a CSV and sends it to the upload page", async () => {
    const { user, click, router, uploads } = open()
    await user.click(screen.getByRole("button", { name: en("intake.attach", "uploads") }))
    expect(click).toHaveBeenCalledTimes(1)
    await user.upload(picker(), file(CSV, "notices-for-october.csv", "text/csv"))
    expect(
      screen.getByRole("button", { name: en("intake.attach", "uploads") }),
    ).toHaveAttribute("data-attached")

    expect(await screen.findByText("2 purchases in the file")).toBeInTheDocument()
    expect(screen.getByText("1 row with errors")).toBeInTheDocument()
    expect(screen.getByTitle("notices-for-october.csv")).toHaveTextContent(
      "notices-for-october.csv",
    )
    expect(screen.getByText(/^\d+ B$/)).toBeInTheDocument()
    expect(
      screen.getByRole("textbox", { name: en("box.noteLabel", "search") }),
    ).toBeInTheDocument()
    await user.click(screen.getByText(en("intake.details", "uploads")))
    expect(screen.getByRole("table")).toBeInTheDocument()

    await user.click(find())
    expect(uploads.create).toHaveBeenCalledWith(
      expect.objectContaining({
        file: expect.objectContaining({ name: "notices-for-october.csv" }),
        check: expect.objectContaining({ total: 3 }),
      }),
    )
    await waitFor(() => expect(router.state.location.pathname).toBe("/uploads/u1"))
  })

  it("opens the only purchase of a file directly", async () => {
    const create = vi.fn(async () => uploadSummary({ id: "u7", total: 1 }))
    const { user, router } = open(stubGateway({ create }))
    await user.upload(picker(), file("lot_id;procedure_name\nL9;Paper", "one.csv"))
    await screen.findByText("1 purchase in the file")
    await user.click(find())
    await waitFor(() => expect(router.state.location.pathname).toBe("/uploads/u7/lots/L9"))
  })

  it("highlights the panel while a file is dragged and attaches the dropped one", async () => {
    open()
    fireEvent(window, dragEvent("dragenter"))
    expect(field()).toHaveAttribute("data-dropping")
    expect(screen.getByText(en("box.drop", "search"))).toBeInTheDocument()
    fireEvent(window, dragEvent("dragover"))
    fireEvent(window, dragEvent("dragleave"))
    expect(field()).not.toHaveAttribute("data-dropping")
    fireEvent(window, new Event("dragenter"))
    expect(field()).not.toHaveAttribute("data-dropping")
    fireEvent(window, dragEvent("dragenter"))
    fireEvent(window, dragEvent("drop", [file(CSV, "dropped.csv")]))
    expect(field()).not.toHaveAttribute("data-dropping")
    expect(await screen.findByTitle("dropped.csv")).toBeInTheDocument()
  })

  it("removes the file and returns to a plain description", async () => {
    const { user } = open()
    await user.upload(picker(), file(CSV, "notices.csv"))
    await screen.findByTitle("notices.csv")
    await user.click(screen.getByRole("button", { name: /^Remove file notices\.csv/ }))
    await waitFor(() => expect(screen.queryByTitle("notices.csv")).toBeNull())
    const description = screen.getByRole("textbox", { name: en("box.label", "search") })
    expect(description).toHaveFocus()
    expect(screen.queryByText("2 purchases in the file")).toBeNull()
  })

  it("accepts a PDF honestly and searches by the text instead", async () => {
    const { user, router, uploads } = open()
    await user.upload(picker(), file("%PDF-1.7 spec", "terms.pdf", "application/pdf"))
    expect(await screen.findByText(en("intake.later", "uploads"))).toBeInTheDocument()
    expect(screen.getByText("PDF")).toBeInTheDocument()
    expect(find()).toHaveAttribute("aria-disabled", "true")
    await user.click(find())
    expect(await screen.findByRole("alert")).toHaveTextContent(en("file_needs_text", "errors"))
    expect(uploads.create).not.toHaveBeenCalled()

    const description = screen.getByRole("textbox", { name: en("box.label", "search") })
    await user.type(description, "paper A4")
    expect(find()).not.toHaveAttribute("aria-disabled", "true")
    await user.click(find())
    expect(uploads.create).toHaveBeenCalledWith(
      expect.objectContaining({
        file: expect.objectContaining({ name: "search.csv" }),
        check: expect.objectContaining({
          notices: [expect.objectContaining({ title: "paper A4" })],
        }),
      }),
    )
    await waitFor(() => expect(router.state.location.pathname).toBe("/uploads/u1/lots/query"))
  })

  it("forgets the missing text problem once the file is gone", async () => {
    const { user } = open()
    await user.upload(picker(), file("PK zip", "table.xlsx"))
    await screen.findByText(en("intake.later", "uploads"))
    await user.click(find())
    await screen.findByText(en("file_needs_text", "errors"))
    await user.click(screen.getByRole("button", { name: /^Remove file table\.xlsx/ }))
    expect(screen.queryByText(en("file_needs_text", "errors"))).toBeNull()
  })

  it("rejects a file over 10 MB and offers another one", async () => {
    const { user, click } = open()
    const large = file("lot_id", "huge.csv")
    Object.defineProperty(large, "size", { value: 11 * 1024 * 1024 })
    await user.upload(picker(), large)
    expect(await screen.findByRole("alert")).toHaveTextContent("The file is larger than 10 MB")
    expect(screen.getByText("11 MB")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: en("intake.replace", "uploads") }))
    expect(click).toHaveBeenCalledTimes(1)
  })

  it("rejects an unsupported format and a damaged document", async () => {
    open()
    fireEvent(window, dragEvent("drop", [file("png", "photo.png")]))
    expect(await screen.findByRole("alert")).toHaveTextContent(
      en("intake.rejected.unsupported", "uploads"),
    )
    fireEvent(window, dragEvent("drop", [file("hello", "broken.docx")]))
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        en("intake.rejected.unreadable", "uploads"),
      ),
    )
    fireEvent(window, dragEvent("drop", [file("", "empty.txt")]))
    expect(await screen.findByTitle("empty.txt")).toBeInTheDocument()
  })

  it("explains a CSV without the required columns", async () => {
    const { user, uploads } = open()
    await user.upload(picker(), file("name;price\nFood;1", "wrong.csv"))
    const problem = await screen.findByRole("alert")
    expect(within(problem).getByRole("heading")).toHaveTextContent(
      en("problem.missingColumns.title", "notices"),
    )
    await user.type(screen.getByRole("textbox", { name: en("box.label", "search") }), "food")
    await user.click(find())
    expect(uploads.create).toHaveBeenCalledWith(
      expect.objectContaining({ file: expect.objectContaining({ name: "search.csv" }) }),
    )
  })

  it("warns when no row of a CSV can be processed", async () => {
    const { user } = open()
    await user.upload(picker(), file("lot_id;procedure_name\nbad id!;Food", "rows.csv"))
    expect(await screen.findByText(en("intake.noValid", "uploads"))).toBeInTheDocument()
    expect(screen.getByText("0 purchases in the file")).toBeInTheDocument()
  })

  it("keeps the latest file when an earlier one finishes reading later", async () => {
    const { user } = open()
    await user.upload(picker(), file(CSV, "first.csv"))
    await user.upload(picker(), file("%PDF-1", "second.pdf"))
    expect(await screen.findByText(en("intake.later", "uploads"))).toBeInTheDocument()
    expect(screen.queryByTitle("first.csv")).toBeNull()
  })
})
