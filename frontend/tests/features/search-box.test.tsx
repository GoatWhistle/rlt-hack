import { fireEvent, screen, waitFor } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { stubGateway, uploadSummary } from "@tests/support/gateway"
import { renderWithProviders } from "@tests/support/render"
import { describe, expect, it, vi } from "vitest"
import { DEFAULT_REGION_CODE } from "@/entities/evidence/regions"
import { decodeFile } from "@/entities/notice/decode"
import { MAX_QUERY_LENGTH } from "@/entities/search/model"
import type { UploadGateway } from "@/entities/upload/gateway"
import { UploadGatewayProvider } from "@/entities/upload/gateway-context"
import { COUNTER_FROM, FINE_POINTER, SearchBox } from "@/features/search-box"
import { textUpload } from "@/features/search-box/text-upload"
import { ApiError } from "@/shared/api/api-error"

function renderBox(gateway: UploadGateway = stubGateway(), initialText = "") {
  const onFound = vi.fn()
  const view = renderWithProviders(
    <UploadGatewayProvider gateway={gateway}>
      <SearchBox initialText={initialText} onFound={onFound} />
    </UploadGatewayProvider>,
  )
  const field = screen.getByRole("textbox", { name: en("box.label", "search") })
  return { ...view, onFound, field, gateway }
}

async function sentCsv(gateway: UploadGateway): Promise<string> {
  const [request] = vi.mocked(gateway.create).mock.calls.at(-1) ?? []
  if (!request) throw new Error("nothing was sent")
  return decodeFile(request.file)
}

describe("the search box", () => {
  it("encodes punctuation and region in the same CSV format as file upload", async () => {
    const source = textUpload('rice; "premium"\noats', "78")
    expect(source.check.ok && source.check.notices[0]?.title).toBe('rice; "premium"\noats')
    expect(await decodeFile(source.file)).toBe(
      'lot_id;procedure_name;delivery_region\nquery;"rice; ""premium""\noats";"78"\n',
    )
  })

  it("uses the upload recommendation for a text query", async () => {
    const upload = stubGateway()
    const { user } = renderWithProviders(
      <UploadGatewayProvider gateway={upload}>
        <SearchBox initialText="rice" onFound={vi.fn()} />
      </UploadGatewayProvider>,
    )
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    await waitFor(() => expect(upload.create).toHaveBeenCalledTimes(1))
  })

  it("sends a regional preference without restricting the candidate pool", async () => {
    const { user, field, gateway } = renderBox()
    await user.click(screen.getByRole("button", { name: /^Delivery region:/ }))
    await user.type(screen.getByRole("combobox"), "msk{Enter}")
    await user.type(field, "paper")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    await waitFor(() =>
      expect(gateway.create).toHaveBeenCalledWith(
        expect.objectContaining({ check: expect.objectContaining({ total: 1 }) }),
      ),
    )
    expect(await sentCsv(gateway)).toContain(';"77"')
  })

  it("leaves the region out once the preference is switched off", async () => {
    const { user, field, gateway } = renderBox()
    await user.click(screen.getByRole("button", { name: /^Delivery region:/ }))
    await user.click(screen.getByRole("option", { name: en("box.anyRegion", "search") }))
    await user.type(field, "paper")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    await waitFor(() => expect(gateway.create).toHaveBeenCalledTimes(1))
    expect(await sentCsv(gateway)).toContain(';""')
  })
  it("sends the text from the button and reports the result", async () => {
    const { user, field, onFound, gateway } = renderBox()
    await user.type(field, "  rice 200 kg  ")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    await waitFor(() => expect(onFound).toHaveBeenCalledWith(uploadSummary(), ["query"]))
    expect(gateway.create).toHaveBeenCalledWith(
      expect.objectContaining({
        check: expect.objectContaining({
          notices: [expect.objectContaining({ title: "rice 200 kg" })],
        }),
      }),
    )
    expect(await sentCsv(gateway)).toContain(`;"${DEFAULT_REGION_CODE}"`)
  })

  it("starts a new line on Enter and sends only from the button", async () => {
    const { user, field, gateway } = renderBox()
    await user.type(field, "rice{Enter}oats")
    expect(field).toHaveValue("rice\noats")
    await user.type(field, "{Control>}{Enter}{/Control}")
    expect(gateway.create).not.toHaveBeenCalled()
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    await waitFor(() => expect(gateway.create).toHaveBeenCalledTimes(1))
  })

  it("asks for text before sending an empty query", async () => {
    const { user, field, gateway } = renderBox()
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(screen.getByRole("alert")).toHaveTextContent(en("empty_query", "errors"))
    expect(field).toHaveAttribute("aria-invalid", "true")
    await user.type(field, "x")
    expect(screen.queryByRole("alert")).toBeNull()
    expect(gateway.create).not.toHaveBeenCalled()
  })

  it("counts characters near the limit and refuses a text that is too long", async () => {
    const { user, field, gateway } = renderBox(stubGateway(), "a".repeat(COUNTER_FROM - 1))
    expect(screen.queryByText(/ \/ /)).toBeNull()
    fireEvent.change(field, { target: { value: "a".repeat(MAX_QUERY_LENGTH + 1) } })
    expect(screen.getByText("4,001 / 4,000")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(screen.getByRole("alert")).toHaveTextContent(en("query_too_long", "errors"))
    expect(gateway.create).not.toHaveBeenCalled()
  })

  it("explains a refusal from the server by its code and clears it on edit", async () => {
    const search = vi.fn(async () => {
      throw new ApiError({ status: 422, code: "query_not_understood" })
    })
    const { user, field } = renderBox(stubGateway({ create: search }))
    await user.type(field, "??")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(await screen.findByRole("alert")).toHaveTextContent(
      en("query_not_understood", "errors"),
    )
    await user.type(field, "x")
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("shows that a search is running and ignores repeated sends", async () => {
    let finish: (value: ReturnType<typeof uploadSummary>) => void = () => undefined
    const search = vi.fn(
      () =>
        new Promise<ReturnType<typeof uploadSummary>>((resolve) => {
          finish = resolve
        }),
    )
    const { user, field } = renderBox(stubGateway({ create: search }))
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
    finish(uploadSummary())
    await waitFor(() => expect(button).not.toHaveAttribute("aria-busy"))
    expect(screen.queryByText(en("box.stage.companies", "search"))).toBeNull()
    expect(screen.getByRole("status")).toBeEmptyDOMElement()
  })

  it("keeps the field neutral on a server failure and retries the same text", async () => {
    const search = vi
      .fn()
      .mockRejectedValueOnce(new ApiError({ status: 503, code: "search_busy" }))
      .mockResolvedValue(uploadSummary())
    const { user, field, onFound } = renderBox(stubGateway({ create: search }))
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
    let finish: (value: ReturnType<typeof uploadSummary>) => void = () => undefined
    const search = vi.fn(
      () =>
        new Promise<ReturnType<typeof uploadSummary>>((resolve) => {
          finish = resolve
        }),
    )
    const { user } = renderWithProviders(
      <UploadGatewayProvider gateway={stubGateway({ create: search })}>
        <button type="button">elsewhere</button>
        <SearchBox compact shortcut initialText="rice" onStage={onStage} onFound={vi.fn()} />
      </UploadGatewayProvider>,
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
    finish(uploadSummary())
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
      <UploadGatewayProvider gateway={stubGateway()}>
        <SearchBox autoFocus initialText="oats" onFound={vi.fn()} />
      </UploadGatewayProvider>,
    )
    expect(screen.getByRole("textbox", { name: en("box.label", "search") })).toHaveFocus()
    Object.assign(window, { matchMedia: undefined })
  })

  it("names the field without a visible label in its compact form", () => {
    renderWithProviders(
      <UploadGatewayProvider gateway={stubGateway()}>
        <SearchBox compact inputId="query" onFound={vi.fn()} />
      </UploadGatewayProvider>,
    )
    const field = screen.getByRole("textbox", { name: en("box.label", "search") })
    expect(field).toHaveAttribute("id", "query")
    expect(field).toHaveAttribute("rows", "1")
  })
})
