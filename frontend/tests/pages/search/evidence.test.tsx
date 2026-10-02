import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { contract, contractResult, renderSearch, stubSearch } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import { parseSearchResult } from "@/entities/search/parse"

function region(name: string) {
  return screen.getByRole("region", { name })
}

async function openContract() {
  const view = renderSearch("/search/1f0c")
  await screen.findByRole("heading", { level: 1 })
  return view
}

async function openVariant(
  change: (payload: Record<string, unknown>) => Record<string, unknown>,
) {
  const result = contractResult(change)
  const view = renderSearch(`/search/${result.searchId}`, {
    gateway: stubSearch({ get: vi.fn(async () => result) }),
  })
  await screen.findByRole("heading", { level: 1 })
  return view
}

describe("novelty and origin", () => {
  it("marks a new supplier and explains the archive check and the channels", async () => {
    await openVariant((payload) => ({
      ...payload,
      candidates: (payload.candidates as Record<string, unknown>[]).map((item, index) =>
        index === 0 ? { ...item, novelty: "new" } : item,
      ),
    }))
    const candidates = region(en("candidates.title", "search"))
    expect(within(candidates).getByText(en("novelty.new", "evidence"))).toBeInTheDocument()
    expect(within(candidates).queryByText(en("novelty.unknown", "evidence"))).toBeNull()
    const grounds = screen.getByRole("article")
    expect(
      within(grounds).getByText(
        /absent from the source supplier archive \(set inn-3f2a9c41d0b7e65a\)/,
      ),
    ).toBeInTheDocument()
    expect(within(grounds).getByText("catalog and procurement history")).toBeInTheDocument()
  })

  it("does not claim novelty without a verifiable inn", async () => {
    const view = await openContract()
    await view.user.click(
      within(region(en("candidates.title", "search"))).getByRole("button", {
        name: /Зерновой Двор/,
      }),
    )
    expect(
      within(screen.getByRole("article")).getByText(en("evidence.noveltyUnknown", "search")),
    ).toBeInTheDocument()
  })
})

describe("offer evidence and requirements", () => {
  async function openRequirements() {
    const result = parseSearchResult(contract("search/cases/requirements.example.json"))
    const view = renderSearch(`/search/${result.searchId}`, {
      gateway: stubSearch({ get: vi.fn(async () => result) }),
    })
    await screen.findByRole("heading", { level: 1 })
    return view
  }

  async function pick(view: Awaited<ReturnType<typeof openRequirements>>, name: RegExp) {
    await view.user.click(
      within(region(en("candidates.title", "search"))).getByRole("button", { name }),
    )
    return screen.getByRole("article")
  }

  it("lists the required parameters of the item", async () => {
    await openRequirements()
    expect(screen.getByText("Required: А4, 80 г/м2")).toBeInTheDocument()
  })

  it("shows a matching card with the confirmed parameters and the link method", async () => {
    const view = await openRequirements()
    const grounds = await pick(view, /Офис Снаб/)
    expect(within(grounds).getByText("80 г/м2 — confirmed")).toBeInTheDocument()
    expect(
      within(grounds).getByText(/matched to the catalog · in stock per the source/),
    ).toBeInTheDocument()
  })

  it("never presents a contradicting card as a confirmation", async () => {
    const view = await openRequirements()
    const grounds = await pick(view, /Формат/)
    expect(within(grounds).getByText("А4 — the card says A3")).toBeInTheDocument()
    expect(within(grounds).getByText("80 г/м2 — the card says 65 г/м2")).toBeInTheDocument()
    expect(within(grounds).getByText(/contradicts a required parameter/)).toBeInTheDocument()
  })

  it("keeps a missing parameter unknown and the stale card dated", async () => {
    const view = await openRequirements()
    const incomplete = await pick(view, /Бумажный Двор/)
    expect(within(incomplete).getByText("80 г/м2 — not stated in the card")).toBeInTheDocument()
    expect(within(incomplete).getByText(/availability not stated/)).toBeInTheDocument()
    const stale = await pick(view, /Архивная Бумага/)
    expect(within(stale).getByText(/withdrawn/)).toBeInTheDocument()
    expect(within(stale).getByText(/Mar 1, 2025/)).toBeInTheDocument()
  })
})

describe("the role basis", () => {
  it("ties a role from an offer card to that product", async () => {
    await openContract()
    const grounds = screen.getByRole("article")
    expect(
      within(grounds).getByText(/applies to that product, not the whole range/),
    ).toBeInTheDocument()
  })

  it("separates an okved rule from a confirmation and shows a conflict", async () => {
    await openVariant((payload) => ({
      ...payload,
      candidates: (payload.candidates as Record<string, unknown>[]).map((item, index) =>
        index === 0
          ? {
              ...item,
              roleBasis: "okved",
              roleNote: "Основной ОКВЭД 46.38",
              roleConflict: true,
              roleProduct: null,
            }
          : item,
      ),
    }))
    const grounds = screen.getByRole("article")
    expect(within(grounds).getByText(/a rule, not a confirmation/)).toBeInTheDocument()
    expect(within(grounds).getByText(/Sources disagree, check required/)).toBeInTheDocument()
  })
})

describe("incomplete company cards", () => {
  it("shows a clear identifier and the reason when the name is missing", async () => {
    await openVariant((payload) => ({
      ...payload,
      candidates: (payload.candidates as Record<string, unknown>[]).map((item, index) =>
        index === 0 ? { ...item, name: "", nameSource: "missing" } : item,
      ),
    }))
    const grounds = screen.getByRole("article")
    expect(within(grounds).getAllByText("Company with INN 7801234567").length).toBeGreaterThan(
      0,
    )
    expect(within(grounds).getByText(/No name was found in the sources/)).toBeInTheDocument()
  })

  it("names the matching product on the first screen", async () => {
    await openContract()
    expect(
      within(screen.getByRole("article")).getByText(/Product: “Крупа гречневая ядрица/),
    ).toBeInTheDocument()
  })
})

describe("the inputs note", () => {
  it("says which fields shaped the result and which the model ignored", async () => {
    await openVariant((payload) => ({
      ...payload,
      query: {
        ...(payload.query as Record<string, unknown>),
        context: { customerInn: "7807022750", startPrice: "100.00" },
      },
    }))
    expect(screen.getByText(/Used for matching: description\./)).toBeInTheDocument()
    expect(
      screen.getByText(
        /not used by the current model \(text mode\): customer INN and start price/,
      ),
    ).toBeInTheDocument()
  })
})

describe("the coverage matrix", () => {
  it("opens on request and leads from a cell to the grounds", async () => {
    const view = await openContract()
    await view.user.click(screen.getByRole("button", { name: "Show item coverage" }))
    const matrix = screen.getByRole("region", { name: "Item coverage" })
    expect(within(matrix).getAllByRole("row")).toHaveLength(3)
    expect(screen.getByText(/never added to the confirmed count/)).toBeInTheDocument()
    await view.user.click(
      within(matrix).getAllByRole("button", { name: /Зерновой Двор/ })[0] as HTMLElement,
    )
    expect(screen.getByRole("article", { name: /Зерновой Двор/ })).toBeInTheDocument()
  })
})

describe("comparing chosen candidates", () => {
  it("uses the same items and states for every chosen company", async () => {
    const view = await openContract()
    const compare = screen.getByRole("button", { name: /Compare chosen/ })
    expect(compare).toBeDisabled()
    const list = region(en("candidates.title", "search"))
    for (const name of [/Северный Провиант/, /Зерновой Двор/]) {
      await view.user.click(within(list).getByRole("button", { name }))
      await view.user.click(
        within(screen.getByRole("article")).getByRole("button", { name: /choose candidate/i }),
      )
    }
    await view.user.click(screen.getByRole("button", { name: "Compare chosen (2)" }))
    const dialog = screen.getByRole("dialog", { name: "Compare chosen candidates" })
    expect(within(dialog).getAllByRole("row")).toHaveLength(3)
    expect(within(dialog).getAllByRole("columnheader")).toHaveLength(3)
  })
})
