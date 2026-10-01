import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import {
  lotSummary,
  renderPage,
  stubGateway,
  uploadDetail,
  uploadSummary,
} from "@tests/support/gateway"
import { describe, expect, it, vi } from "vitest"
import { SAMPLE_PATH } from "@/pages/uploads/intro"

const CSV = [
  "lot_id;procedure_name;start_price;extra",
  "1;Food;100;a",
  "2;Paper;bad;b",
  "3;Ink;5;c",
].join("\n")

function csv(content = CSV, name = "notices.csv") {
  return new File([content], name, { type: "text/csv" })
}

describe("the first visit", () => {
  it("explains the format and checks the file before processing", async () => {
    const gateway = stubGateway({
      get: vi.fn(async () => uploadDetail([lotSummary("1")])),
    })
    const { user, router } = renderPage("/uploads", gateway)
    expect(
      await screen.findByRole("heading", { level: 1, name: en("intro.title", "uploads") }),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: en("intro.sample", "uploads") })).toHaveAttribute(
      "href",
      SAMPLE_PATH,
    )
    expect(screen.getByText(en("demoNote"))).toBeInTheDocument()
    await user.upload(screen.getByLabelText(en("drop.choose", "uploads")), csv())

    const dialog = await screen.findByRole("dialog", { name: en("dialog.title", "uploads") })
    expect(await within(dialog).findByText("notices.csv")).toBeInTheDocument()
    const steps = within(dialog).getByRole("list", {
      name: en("dialog.steps.label", "uploads"),
    })
    expect(within(steps).getByText(en("dialog.steps.check", "uploads"))).toHaveAttribute(
      "aria-current",
      "step",
    )
    expect(within(dialog).getByText("extra — not used")).toBeInTheDocument()
    expect(
      within(dialog).getByRole("region", { name: en("dialog.previewRegion", "uploads") }),
    ).toBeInTheDocument()
    expect(within(dialog).getByText("Error in 1 row")).toBeInTheDocument()
    expect(within(dialog).getByText("Row 3")).toBeInTheDocument()
    expect(within(dialog).getByText("start price “bad” is not a number")).toBeInTheDocument()

    await user.click(within(dialog).getByRole("button", { name: "Process 2 purchases" }))
    await waitFor(() => expect(router.state.location.pathname).toBe("/uploads/u1"))
    const [created] = vi.mocked(gateway.create).mock.calls[0] ?? []
    expect(created?.check.ok && created.check.notices.map((notice) => notice.lotId)).toEqual([
      "1",
      "3",
    ])
  })

  it("explains a file it cannot use and lets the user pick another", async () => {
    const { user } = renderPage("/uploads", stubGateway())
    await user.upload(
      await screen.findByLabelText(en("drop.choose", "uploads")),
      csv("lot_id;price\n1;2", "wrong.csv"),
    )
    const dialog = await screen.findByRole("dialog")
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      en("problem.missingColumns.title", "notices"),
    )
    expect(within(dialog).queryByRole("button", { name: /Process/ })).not.toBeInTheDocument()
    await user.click(
      within(dialog).getByRole("button", { name: en("dialog.otherFile", "uploads") }),
    )
    await user.upload(
      within(dialog).getByLabelText(en("drop.choose", "uploads")),
      csv("lot_id;procedure_name\n;Food", "x.csv"),
    )
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      en("dialog.noValid", "uploads"),
    )
  })

  it("reports a file that cannot be read", async () => {
    const { user } = renderPage("/uploads", stubGateway())
    const broken = csv()
    Object.assign(broken, { arrayBuffer: () => Promise.reject(new Error("io")) })
    await user.upload(await screen.findByLabelText(en("drop.choose", "uploads")), broken)
    expect(await screen.findByRole("alert")).toHaveTextContent(
      en("problem.unreadable.title", "notices"),
    )
  })
})

describe("the list of uploads", () => {
  it("shows each file with its processing state and opens a new upload", async () => {
    const gateway = stubGateway({
      list: vi.fn(async () => [
        uploadSummary({ id: "a", fileName: "done.csv", rejected: 2 }),
        uploadSummary({
          id: "b",
          fileName: "running.csv",
          total: 10,
          processed: 4,
          stored: false,
        }),
      ]),
    })
    const { user } = renderPage("/uploads", gateway)
    expect(
      await screen.findByRole("heading", { level: 1, name: en("list.title", "uploads") }),
    ).toBeInTheDocument()
    const done = screen.getByRole("link", { name: /done\.csv/ })
    expect(done).toHaveAttribute("href", "/uploads/a")
    expect(within(done).getByText(en("list.done", "uploads"))).toBeInTheDocument()
    expect(within(done).getByText("2 rows with errors were not processed")).toBeInTheDocument()
    const running = screen.getByRole("link", { name: /running\.csv/ })
    expect(within(running).getByText("Processed 4 of 10")).toBeInTheDocument()
    expect(within(running).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "4")
    expect(within(running).getByText(en("list.notStored", "uploads"))).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: en("list.upload", "uploads") }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByLabelText(en("drop.choose", "uploads"))).toBeInTheDocument()
    await user.click(within(dialog).getByRole("button", { name: en("action.close") }))
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
  })

  it("offers a retry when the list cannot load", async () => {
    const gateway = stubGateway({
      list: vi.fn(async () => {
        throw new Error("down")
      }),
    })
    renderPage("/uploads", gateway)
    expect(
      await screen.findByRole("button", { name: en("action.retry") }, { timeout: 6000 }),
    ).toBeInTheDocument()
  })
})
