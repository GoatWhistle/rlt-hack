import { fireEvent, screen, waitFor } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { contractResult, stubSearch } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import type { SearchGateway } from "@/entities/search/gateway"
import { SearchGatewayProvider } from "@/entities/search/gateway-context"
import { MAX_QUERY_LENGTH } from "@/entities/search/model"
import { COUNTER_FROM, PICK_TO_FIELD, SearchBox } from "@/features/search-box"
import { ApiError } from "@/shared/api/api-error"

function renderBox(gateway: SearchGateway = stubSearch(), initialText = "") {
  const onFound = vi.fn()
  const view = renderWithProviders(
    <SearchGatewayProvider gateway={gateway}>
      <SearchBox initialText={initialText} onFound={onFound} />
    </SearchGatewayProvider>,
  )
  const field = screen.getByRole("textbox", { name: en("box.label", "search") })
  return { ...view, onFound, field, gateway }
}

describe("the search box", () => {
  it("sends the text on Enter and reports the result", async () => {
    const { user, field, onFound, gateway } = renderBox()
    await user.type(field, "  rice 200 kg  {Enter}")
    await waitFor(() => expect(onFound).toHaveBeenCalledWith(contractResult()))
    expect(gateway.search).toHaveBeenCalledWith({ text: "rice 200 kg", limit: 20 })
  })

  it("starts a new line on Shift+Enter and sends on Ctrl+Enter", async () => {
    const { user, field, gateway } = renderBox()
    await user.type(field, "rice{Shift>}{Enter}{/Shift}oats")
    expect(field).toHaveValue("rice\noats")
    expect(gateway.search).not.toHaveBeenCalled()
    await user.type(field, "{Control>}{Enter}{/Control}")
    await waitFor(() => expect(gateway.search).toHaveBeenCalledTimes(1))
  })

  it("puts an example into the field on a narrow screen and waits for Enter", async () => {
    Object.assign(window, {
      matchMedia: (query: string) => ({
        matches: query === PICK_TO_FIELD,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }),
    })
    const { user, field, gateway } = renderBox()
    const example = en("box.example.groats", "search")
    await user.click(screen.getByRole("button", { name: example }))
    expect(field).toHaveValue(example)
    expect(field).toHaveFocus()
    expect(gateway.search).not.toHaveBeenCalled()
    Object.assign(window, { matchMedia: undefined })
  })

  it("searches right away from an example and keeps it in the field", async () => {
    const { user, field, gateway, onFound } = renderBox()
    const example = en("box.example.office", "search")
    await user.click(screen.getByRole("button", { name: example }))
    expect(field).toHaveValue(example)
    expect(gateway.search).toHaveBeenCalledWith({ text: example, limit: 20 })
    await waitFor(() => expect(onFound).toHaveBeenCalled())
  })

  it("asks for text before sending an empty query", async () => {
    const { user, field, gateway } = renderBox()
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(screen.getByRole("alert")).toHaveTextContent(en("empty_query", "errors"))
    expect(field).toHaveAttribute("aria-invalid", "true")
    await user.type(field, "x")
    expect(screen.queryByRole("alert")).toBeNull()
    expect(gateway.search).not.toHaveBeenCalled()
  })

  it("counts characters near the limit and refuses a text that is too long", async () => {
    const { user, field, gateway } = renderBox(stubSearch(), "a".repeat(COUNTER_FROM - 1))
    expect(screen.queryByText(/characters/)).toBeNull()
    fireEvent.change(field, { target: { value: "a".repeat(MAX_QUERY_LENGTH + 1) } })
    expect(screen.getByText("4,001 of 4,000 characters")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(screen.getByRole("alert")).toHaveTextContent(en("query_too_long", "errors"))
    expect(gateway.search).not.toHaveBeenCalled()
  })

  it("explains a refusal from the server by its code and clears it on edit", async () => {
    const search = vi.fn(async () => {
      throw new ApiError({ status: 422, code: "query_not_understood" })
    })
    const { user, field } = renderBox(stubSearch({ search }))
    await user.type(field, "??{Enter}")
    expect(await screen.findByRole("alert")).toHaveTextContent(
      en("query_not_understood", "errors"),
    )
    await user.type(field, "x")
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("shows that a search is running and ignores repeated sends", async () => {
    let finish: (value: ReturnType<typeof contractResult>) => void = () => undefined
    const search = vi.fn(
      () =>
        new Promise<ReturnType<typeof contractResult>>((resolve) => {
          finish = resolve
        }),
    )
    const { user, field } = renderBox(stubSearch({ search }))
    await user.type(field, "rice{Enter}")
    const button = screen.getByRole("button", { name: en("box.submit", "search") })
    await waitFor(() => expect(button).toHaveAttribute("aria-busy", "true"))
    expect(button).toHaveAttribute("aria-disabled", "true")
    await user.type(field, "{Enter}")
    expect(search).toHaveBeenCalledTimes(1)
    expect(screen.getByRole("status")).toHaveTextContent(en("box.stage.parse", "search"))
    const example = screen.getByRole("button", { name: en("box.example.office", "search") })
    expect(example).toHaveAttribute("aria-disabled", "true")
    await user.click(example)
    expect(field).toHaveValue("rice")
    expect(
      await screen.findByText(en("box.stage.companies", "search"), undefined, {
        timeout: 2000,
      }),
    ).toBeVisible()
    finish(contractResult())
    await waitFor(() => expect(button).not.toHaveAttribute("aria-busy"))
    expect(screen.queryByText(en("box.stage.companies", "search"))).toBeNull()
    expect(screen.getByRole("status")).toBeEmptyDOMElement()
  })

  it("names the field without a visible label in its compact form", () => {
    renderWithProviders(
      <SearchGatewayProvider gateway={stubSearch()}>
        <SearchBox compact showExamples={false} inputId="query" onFound={vi.fn()} />
      </SearchGatewayProvider>,
    )
    const field = screen.getByRole("textbox", { name: en("box.label", "search") })
    expect(field).toHaveAttribute("id", "query")
    expect(field).toHaveAttribute("rows", "1")
    expect(screen.queryByText(en("box.hint", "search"))).toBeNull()
  })
})
