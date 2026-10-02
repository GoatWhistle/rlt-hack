import { screen } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { describe, expect, it } from "vitest"
import { HistoryChips } from "@/entities/evidence/ui/history-chips"

describe("HistoryChips", () => {
  it("bolds the counts and keeps the facts apart without a separator glyph", () => {
    const { container } = renderWithProviders(<HistoryChips similar={11} wins={4} />)
    expect(container).toHaveTextContent(/^11 similar 4 wins$/)
    expect([...container.querySelectorAll("b")].map((node) => node.textContent)).toEqual([
      "11",
      "4",
    ])
  })

  it("leaves out wins that never happened", () => {
    const { container } = renderWithProviders(<HistoryChips similar={2} wins={0} />)
    expect(container).toHaveTextContent(/^2 similar$/)
  })

  it("says so when there is no history at all", () => {
    renderWithProviders(<HistoryChips similar={0} wins={0} />)
    expect(screen.getByText(en("card.noHistory", "candidate"))).toBeInTheDocument()
  })
})
