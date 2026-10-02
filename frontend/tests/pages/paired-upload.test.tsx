import { screen, waitFor } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderPage, stubGateway } from "@tests/support/gateway"
import { expect, it, vi } from "vitest"

it("attaches, removes and submits the item file with notices", async () => {
  const gateway = stubGateway()
  const { user } = renderPage("/uploads", gateway)
  const notices = new File(["lot_id;procedure_name\n1;Water"], "notices.csv", {
    type: "text/csv",
  })
  const items = new File(["lot_id;product_name;okpd2_code\n1;Water;11.07"], "items.csv", {
    type: "text/csv",
  })
  await user.upload(await screen.findByLabelText(en("drop.choose", "uploads")), notices)
  await user.upload(await screen.findByLabelText(en("items.title", "uploads")), items)
  await user.click(screen.getByRole("button", { name: en("items.remove", "uploads") }))
  expect(
    screen.queryByRole("button", { name: en("items.remove", "uploads") }),
  ).not.toBeInTheDocument()
  await user.upload(screen.getByLabelText(en("items.title", "uploads")), items)
  await user.click(screen.getByRole("button", { name: /Process 1/ }))
  await waitFor(() => expect(gateway.create).toHaveBeenCalled())
  expect(vi.mocked(gateway.create).mock.calls[0]?.[0]).toMatchObject({
    file: notices,
    itemsFile: items,
  })
})
