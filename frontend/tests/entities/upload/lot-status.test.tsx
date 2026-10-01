import { screen } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { describe, expect, it } from "vitest"
import { LotStatusTag } from "@/entities/upload/lot-status"
import { LOT_STATUSES } from "@/entities/upload/model"

describe("LotStatusTag", () => {
  it("gives every status its own text and mark", () => {
    renderWithProviders(
      <ul>
        {LOT_STATUSES.map((status) => (
          <li key={status} data-testid={status}>
            <LotStatusTag status={status} />
          </li>
        ))}
      </ul>,
    )
    const marks = LOT_STATUSES.map((status) => {
      const item = screen.getByTestId(status)
      expect(item).toHaveTextContent(en(`status.${status}`, "lots"))
      const mark = item.querySelector("[aria-hidden='true']")
      expect(mark).not.toBeNull()
      return mark?.outerHTML
    })
    expect(new Set(marks).size).toBe(LOT_STATUSES.length)
  })
})
