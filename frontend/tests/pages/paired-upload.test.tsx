import { screen, waitFor } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { stubGateway } from "@tests/support/gateway"
import { renderSearch } from "@tests/support/search"
import { expect, it, vi } from "vitest"

it("attaches, removes and sends the items file together with the notices", async () => {
  const uploads = stubGateway()
  const { user } = renderSearch("/search", { uploads })
  const notices = new File(["lot_id;procedure_name\n1;Water"], "notices.csv", {
    type: "text/csv",
  })
  const items = new File(["lot_id;product_name;okpd2_code\n1;Water;11.07"], "items.csv", {
    type: "text/csv",
  })
  expect(
    screen.queryByLabelText(en("items.title", "uploads"), { selector: "input" }),
  ).toBeNull()
  const main = document.querySelector<HTMLInputElement>('input[type="file"]')
  if (!main) throw new Error("no file input")
  await user.upload(main, notices)
  await user.upload(
    await screen.findByLabelText(en("items.title", "uploads"), { selector: "input" }),
    items,
  )
  expect(screen.getByText("items.csv")).toBeVisible()
  await user.click(screen.getByRole("button", { name: en("items.remove", "uploads") }))
  expect(screen.queryByText("items.csv")).toBeNull()
  expect(screen.getByRole("button", { name: en("items.add", "uploads") })).toBeVisible()
  await user.upload(
    screen.getByLabelText(en("items.title", "uploads"), { selector: "input" }),
    items,
  )
  await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
  await waitFor(() => expect(uploads.create).toHaveBeenCalled())
  expect(vi.mocked(uploads.create).mock.calls[0]?.[0]).toMatchObject({
    file: notices,
    itemsFile: items,
  })
})
