import { act, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, RouterProvider } from "react-router"
import { describe, expect, it } from "vitest"
import { useQueryState } from "@/shared/routing/use-query-state"

const KEYS = ["company", "view"] as const

function Probe() {
  const [state, update] = useQueryState(KEYS)
  return (
    <>
      <output>{`${state.company ?? "-"}|${state.view ?? "-"}`}</output>
      <button type="button" onClick={() => update({ company: "west", view: null })}>
        west
      </button>
    </>
  )
}

function renderProbe(path: string) {
  const router = createMemoryRouter([{ path: "/lot", Component: Probe }], {
    initialEntries: [path],
  })
  render(<RouterProvider router={router} />)
  return router
}

describe("query state", () => {
  it("reads the address, writes changes back and keeps other parameters", async () => {
    const router = renderProbe("/lot?q=milk&view=list")
    expect(screen.getByRole("status")).toHaveTextContent("-|list")
    await userEvent.click(screen.getByRole("button", { name: "west" }))
    expect(screen.getByRole("status")).toHaveTextContent("west|-")
    expect(router.state.location.search).toBe("?q=milk&company=west")
  })

  it("follows an address changed from outside", async () => {
    const router = renderProbe("/lot?company=north")
    await act(() => router.navigate("/lot?company=south&view=candidates"))
    expect(screen.getByRole("status")).toHaveTextContent("south|candidates")
  })
})
