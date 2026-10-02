import { screen, within } from "@testing-library/react"
import { renderWithProviders } from "@tests/support/render"
import { createRef } from "react"
import { afterEach, describe, expect, it } from "vitest"
import { localJson } from "@/shared/storage/local-json"
import { ResultSection } from "@/shared/ui/result-section"
import { PANE_FOLDS_KEY, WorkspaceLayout } from "@/shared/ui/workspace-layout"

const labels = { list: "Items", candidates: "Candidates", evidence: "Evidence" }

function renderColumns() {
  return renderWithProviders(
    <WorkspaceLayout
      narrow={false}
      legend="Sections"
      labels={labels}
      counts={{ list: 2, candidates: 7 }}
      view="evidence"
      onShow={() => undefined}
      stackRef={createRef()}
      panes={{
        list: (
          <ResultSection title="Items" aside="2 items">
            <ResultSection title="Inner">
              <p>row</p>
            </ResultSection>
          </ResultSection>
        ),
        candidates: (
          <ResultSection title="Candidates">
            <p>card</p>
          </ResultSection>
        ),
        evidence: (
          <ResultSection title="Evidence">
            <p>detail</p>
          </ResultSection>
        ),
      }}
    />,
  )
}

afterEach(() => {
  window.localStorage.clear()
})

describe("the foldable workspace columns", () => {
  it("offers to hide only the list and the candidates, once per pane", () => {
    renderColumns()
    expect(screen.getAllByRole("button", { name: /^Hide/ })).toHaveLength(2)
    expect(screen.getByRole("button", { name: "Hide “Items”" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Hide “Candidates”" })).toBeInTheDocument()
  })

  it("folds a pane into a rail and brings it back with the focus", async () => {
    const { user } = renderColumns()
    const hide = screen.getByRole("button", { name: "Hide “Items”" })
    const pane = document.getElementById(hide.getAttribute("aria-controls") ?? "")
    await user.click(hide)
    const rail = screen.getByRole("button", { name: "Show “Items”" })
    expect(rail).toHaveAttribute("aria-expanded", "false")
    expect(within(rail).getByText("2")).toBeInTheDocument()
    expect(rail).toHaveFocus()
    expect(pane).toHaveAttribute("data-folded")
    expect(localJson.read(PANE_FOLDS_KEY)).toEqual({ list: true, candidates: false })
    await user.click(rail)
    expect(screen.queryByRole("button", { name: "Show “Items”" })).toBeNull()
    expect(pane).not.toHaveAttribute("data-folded")
    expect(screen.getByRole("heading", { name: "Items" })).toHaveFocus()
  })

  it("remembers folded panes and ignores a damaged record", () => {
    localJson.write(PANE_FOLDS_KEY, { list: false, candidates: true })
    const view = renderColumns()
    expect(screen.getByRole("button", { name: "Show “Candidates”" })).toBeInTheDocument()
    view.unmount()
    localJson.write(PANE_FOLDS_KEY, "folded")
    renderColumns()
    expect(screen.queryByRole("button", { name: /^Show/ })).toBeNull()
  })
})
