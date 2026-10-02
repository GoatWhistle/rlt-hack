import { fireEvent, screen, waitFor } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { contractResult, stubSearch } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import type { SearchGateway } from "@/entities/search/gateway"
import { SearchGatewayProvider } from "@/entities/search/gateway-context"
import { MAX_QUERY_LENGTH } from "@/entities/search/model"
import { COUNTER_FROM, FINE_POINTER, SearchBox } from "@/features/search-box"
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
  it("sends a regional preference without restricting the candidate pool", async () => {
    const { user, field, gateway } = renderBox()
    await user.selectOptions(screen.getByRole("combobox"), "78")
    await user.type(field, "paper")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    await waitFor(() =>
      expect(gateway.search).toHaveBeenCalledWith({
        text: "paper",
        limit: 20,
        preferredRegion: "78",
      }),
    )
  })
  it("sends the text from the button and reports the result", async () => {
    const { user, field, onFound, gateway } = renderBox()
    await user.type(field, "  rice 200 kg  ")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    await waitFor(() => expect(onFound).toHaveBeenCalledWith(contractResult()))
    expect(gateway.search).toHaveBeenCalledWith({ text: "rice 200 kg", limit: 20 })
  })

  it("starts a new line on Enter and sends only from the button", async () => {
    const { user, field, gateway } = renderBox()
    await user.type(field, "rice{Enter}oats")
    expect(field).toHaveValue("rice\noats")
    await user.type(field, "{Control>}{Enter}{/Control}")
    expect(gateway.search).not.toHaveBeenCalled()
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    await waitFor(() => expect(gateway.search).toHaveBeenCalledTimes(1))
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
    expect(screen.queryByText(/ \/ /)).toBeNull()
    fireEvent.change(field, { target: { value: "a".repeat(MAX_QUERY_LENGTH + 1) } })
    expect(screen.getByText("4,001 / 4,000")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(screen.getByRole("alert")).toHaveTextContent(en("query_too_long", "errors"))
    expect(gateway.search).not.toHaveBeenCalled()
  })

  it("explains a refusal from the server by its code and clears it on edit", async () => {
    const search = vi.fn(async () => {
      throw new ApiError({ status: 422, code: "query_not_understood" })
    })
    const { user, field } = renderBox(stubSearch({ search }))
    await user.type(field, "??")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
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
    await user.type(field, "rice")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    const button = screen.getByRole("button", { name: en("box.submit", "search") })
    await waitFor(() => expect(button).toHaveAttribute("aria-busy", "true"))
    expect(button).toHaveAttribute("aria-disabled", "true")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(search).toHaveBeenCalledTimes(1)
    expect(screen.getByRole("status")).toHaveTextContent(en("box.stage.parse", "search"))
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

  it("keeps the field neutral on a server failure and retries the same text", async () => {
    const search = vi
      .fn()
      .mockRejectedValueOnce(new ApiError({ status: 503, code: "search_busy" }))
      .mockResolvedValue(contractResult())
    const { user, field, onFound } = renderBox(stubSearch({ search }))
    await user.type(field, "rice")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(await screen.findByRole("alert")).toBeInTheDocument()
    expect(field).not.toHaveAttribute("aria-invalid")
    await user.click(screen.getByRole("button", { name: en("action.retry") }))
    await waitFor(() => expect(onFound).toHaveBeenCalled())
    expect(search).toHaveBeenCalledTimes(2)
  })

  it("marks the field only for a problem with the text itself", async () => {
    const { user, field } = renderBox()
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(field).toHaveAttribute("aria-invalid", "true")
    expect(screen.queryByRole("button", { name: en("action.retry") })).toBeNull()
  })

  it("jumps to the field on / and reports the stage outside", async () => {
    const onStage = vi.fn()
    let finish: (value: ReturnType<typeof contractResult>) => void = () => undefined
    const search = vi.fn(
      () =>
        new Promise<ReturnType<typeof contractResult>>((resolve) => {
          finish = resolve
        }),
    )
    const { user } = renderWithProviders(
      <SearchGatewayProvider gateway={stubSearch({ search })}>
        <button type="button">elsewhere</button>
        <SearchBox compact shortcut initialText="rice" onStage={onStage} onFound={vi.fn()} />
      </SearchGatewayProvider>,
    )
    const field = screen.getByRole("textbox", { name: en("box.label", "search") })
    expect(field).toHaveAttribute("aria-keyshortcuts", "/")
    await user.click(screen.getByRole("button", { name: "elsewhere" }))
    await user.keyboard("/")
    expect(field).toHaveFocus()
    expect(field).toHaveValue("rice")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    await waitFor(() => expect(onStage).toHaveBeenLastCalledWith("parse"))
    expect(screen.queryByText(en("box.stage.parse", "search"))).toBeNull()
    finish(contractResult())
    await waitFor(() => expect(onStage).toHaveBeenLastCalledWith(null))
  })

  it("takes the focus on a screen with a fine pointer", () => {
    Object.assign(window, {
      matchMedia: (query: string) => ({
        matches: query === FINE_POINTER,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }),
    })
    renderWithProviders(
      <SearchGatewayProvider gateway={stubSearch()}>
        <SearchBox autoFocus initialText="oats" onFound={vi.fn()} />
      </SearchGatewayProvider>,
    )
    expect(screen.getByRole("textbox", { name: en("box.label", "search") })).toHaveFocus()
    Object.assign(window, { matchMedia: undefined })
  })

  it("names the field without a visible label in its compact form", () => {
    renderWithProviders(
      <SearchGatewayProvider gateway={stubSearch()}>
        <SearchBox compact inputId="query" onFound={vi.fn()} />
      </SearchGatewayProvider>,
    )
    const field = screen.getByRole("textbox", { name: en("box.label", "search") })
    expect(field).toHaveAttribute("id", "query")
    expect(field).toHaveAttribute("rows", "1")
  })
})
