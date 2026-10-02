import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderPage, stubGateway, uploadSummary } from "@tests/support/gateway"
import { describe, expect, it, vi } from "vitest"
import type { UploadSummary } from "@/entities/upload/model"
import { SAMPLE_PATH } from "@/pages/uploads/format-help"

function csv(
  content = "lot_id;procedure_name;start_price\n1;Food;100\n3;Ink;5",
  name = "notices.csv",
) {
  return new File([content], name, { type: "text/csv" })
}

describe("processing an uploaded file", () => {
  it("shows the processing and offers the file in a toast once the dialog is closed", async () => {
    let finish: (upload: UploadSummary) => void = () => {}
    const create = vi.fn(
      () =>
        new Promise<UploadSummary>((resolve) => {
          finish = resolve
        }),
    )
    const { user, router } = renderPage("/uploads", stubGateway({ create }))
    await user.upload(await screen.findByLabelText(en("drop.choose", "uploads")), csv())
    const dialog = await screen.findByRole("dialog")
    await user.click(
      await within(dialog).findByRole("button", { name: "Process 2\u00a0purchases" }),
    )
    expect(await within(dialog).findByText("Finding suppliers for 2 purchases")).toBeVisible()
    expect(
      within(dialog).getByText(en("dialog.processing.stage.send", "uploads")),
    ).toBeVisible()
    expect(within(dialog).getByText(en("dialog.processing.note", "uploads"))).toBeVisible()
    expect(
      within(dialog).getByRole("button", { name: en("dialog.otherFile", "uploads") }),
    ).toBeDisabled()
    await user.click(within(dialog).getByRole("button", { name: en("action.close") }))
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())
    finish(uploadSummary())
    const open = await screen.findByRole("button", { name: en("dialog.open", "uploads") })
    expect(router.state.location.pathname).toBe("/uploads")
    await user.click(open)
    await waitFor(() => expect(router.state.location.pathname).toBe("/uploads/u1"))
  })

  it("offers the sample file next to a file problem", async () => {
    const { user } = renderPage("/uploads", stubGateway())
    await user.upload(
      await screen.findByLabelText(en("drop.choose", "uploads")),
      csv("lot_id;price\n1;2", "wrong.csv"),
    )
    const alert = await within(await screen.findByRole("dialog")).findByRole("alert")
    expect(within(alert).getByRole("link", { name: en("sample", "notices") })).toHaveAttribute(
      "href",
      SAMPLE_PATH,
    )
  })
})
