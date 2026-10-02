import { screen, within } from "@testing-library/react"
import {
  category,
  quality,
  renderAnalytics,
  run,
  source,
  sourcesReport,
  stubAnalytics,
} from "@tests/support/analytics"
import { en } from "@tests/support/dictionaries"
import { describe, expect, it, vi } from "vitest"
import { ApiError } from "@/shared/api/api-error"

const t = (path: string) => en(path, "analytics")

describe("the categories report", () => {
  it("lists the top level with links one level down and to records", async () => {
    renderAnalytics("/analytics/categories", stubAnalytics())
    const table = await screen.findByRole("table", { name: t("categories.title") })
    expect(within(table).getByRole("link", { name: "01 Name 01" })).toHaveAttribute(
      "href",
      "/analytics/categories/01",
    )
    expect(
      within(table).getByRole("link", { name: t("categories.noCategory") }),
    ).toHaveAttribute("href", "/analytics/records?problem=no_category")
    expect(screen.getByText(t("categories.companiesNote"))).toBeInTheDocument()
    expect(screen.getByText(t("categories.origin.system"))).toBeInTheDocument()
  })

  it("opens a class and shows its groups with the way back", async () => {
    renderAnalytics("/analytics/categories/01?region=78", stubAnalytics())
    const table = await screen.findByRole("table", { name: "Subcategories of 01" })
    expect(within(table).getByRole("link", { name: "01.11 Name 01.11" })).toHaveAttribute(
      "href",
      "/analytics/records?category=01.11&region=78",
    )
    expect(screen.getByRole("link", { name: t("categories.all") })).toHaveAttribute(
      "href",
      "/analytics/categories?region=78",
    )
    expect(screen.getByRole("link", { name: t("categories.showRecords") })).toBeInTheDocument()
  })

  it("handles an empty classification and failure", async () => {
    const empty = vi.fn(async () => ({
      meta: sourcesReport().meta,
      offers: 0,
      items: [],
      origins: [],
    }))
    renderAnalytics("/analytics/categories", stubAnalytics({ categories: empty }))
    expect(await screen.findByText(t("categories.empty"))).toBeInTheDocument()
    const broken = vi.fn(async () => {
      throw new ApiError({ status: 500, code: "internal" })
    })
    renderAnalytics("/analytics/categories", stubAnalytics({ categories: broken }))
    expect(await screen.findAllByRole("button", { name: en("action.retry") })).not.toHaveLength(
      0,
    )
  })

  it("keeps a row's category without a name readable", async () => {
    const gateway = stubAnalytics({
      categories: vi.fn(async () => ({
        meta: sourcesReport().meta,
        offers: 6,
        items: [category("07", "", { name: "" })],
        origins: [],
      })),
    })
    renderAnalytics("/analytics/categories", gateway)
    expect(await screen.findByRole("link", { name: "07" })).toBeInTheDocument()
  })
})

describe("the quality report", () => {
  it("shows age buckets, availability and a problem matrix linked to records", async () => {
    renderAnalytics("/analytics/quality", stubAnalytics())
    const matrix = await screen.findByRole("table", { name: t("quality.matrixTitle") })
    const links = within(matrix).getAllByRole("link")
    expect(links[0]).toHaveAttribute("href", "/analytics/records?problem=no_supplier&source=a")
    expect(screen.getByText(t("quality.age.d1"))).toBeInTheDocument()
    expect(screen.getByText(t("quality.availability.available"))).toBeInTheDocument()
    expect(screen.getByText(t("ratio.noBase"))).toBeInTheDocument()
  })

  it("says so when no source has offers", async () => {
    renderAnalytics(
      "/analytics/quality",
      stubAnalytics({ quality: vi.fn(async () => quality({ problems: [] })) }),
    )
    expect(await screen.findByText(t("quality.empty"))).toBeInTheDocument()
  })
})

describe("the sources report", () => {
  it("separates never-run and failed sources and shows the run journal", async () => {
    const report = sourcesReport({
      items: [
        source("a", { state: "failed" }),
        source("b", { state: "never_run", lastSuccessAt: undefined }),
      ],
      runs: [run("r1"), run("r2", { status: "success", errorMessage: "" })],
    })
    renderAnalytics("/analytics/sources", stubAnalytics({ sources: vi.fn(async () => report) }))
    expect((await screen.findAllByText(t("sources.state.failed"))).length).toBeGreaterThan(0)
    expect(screen.getByText(t("sources.state.never_run"))).toBeInTheDocument()
    expect(screen.getByText("boom")).toBeInTheDocument()
    expect(screen.getAllByText("2 companies · 4 offers").length).toBe(2)
    expect(screen.getByText(/1 partial/)).toBeInTheDocument()
  })

  it("handles no sources, no runs and failure", async () => {
    renderAnalytics(
      "/analytics/sources",
      stubAnalytics({ sources: vi.fn(async () => sourcesReport({ items: [] })) }),
    )
    expect(await screen.findByText(t("sources.noSources"))).toBeInTheDocument()
    renderAnalytics(
      "/analytics/sources",
      stubAnalytics({ sources: vi.fn(async () => sourcesReport({ runs: [], partial: 0 })) }),
    )
    expect(await screen.findByText(t("sources.noRuns"))).toBeInTheDocument()
    const broken = vi.fn(async () => {
      throw new ApiError({ status: 500, code: "internal" })
    })
    renderAnalytics("/analytics/sources", stubAnalytics({ sources: broken }))
    expect(await screen.findAllByRole("button", { name: en("action.retry") })).not.toHaveLength(
      0,
    )
  })
})
