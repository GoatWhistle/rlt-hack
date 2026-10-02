import { screen } from "@testing-library/react"
import { renderWithProviders } from "@tests/support/render"
import { expect, it } from "vitest"
import { MatchRow } from "@/entities/evidence/ui/match-row"

it("labels archive evidence as historical and dates the procurement without stock claims", () => {
  renderWithProviders(
    <MatchRow
      name="Paper A4"
      basis="historical"
      source={{
        kind: "purchase",
        title: "Office paper procurement",
        url: "/uploads/u1/lots/paper/evidence/1/archive-1",
        checkedAt: "2025-02-01",
      }}
    />,
  )
  expect(
    screen.getByText("Item in a procurement with this company participating"),
  ).toBeVisible()
  expect(screen.getByRole("link", { name: /Office paper procurement/ })).toHaveAttribute(
    "href",
    "/uploads/u1/lots/paper/evidence/1/archive-1",
  )
  expect(screen.getByText(/procurement date/)).toBeVisible()
  expect(screen.queryByText("In stock", { exact: true })).toBeNull()
})
