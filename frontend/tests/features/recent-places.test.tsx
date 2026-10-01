import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { stubGateway, uploadSummary } from "@tests/support/gateway"
import { renderWithProviders } from "@tests/support/render"
import { stubSearch } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import { SearchGatewayProvider } from "@/entities/search/gateway-context"
import { UploadGatewayProvider } from "@/entities/upload/gateway-context"
import { RECENT_FILES, RecentPlaces } from "@/features/recent-places"

function renderRecent(files: number, searches: number) {
  const uploads = stubGateway({
    list: vi.fn(async () =>
      Array.from({ length: files }, (_, index) =>
        uploadSummary({ id: `u${index}`, fileName: `file-${index}.csv` }),
      ),
    ),
  })
  const search = stubSearch({
    recent: vi.fn(async () =>
      Array.from({ length: searches }, (_, index) => ({
        searchId: `s${index}`,
        text: `rice ${index}`,
        locale: "en" as const,
        items: 1,
        candidates: 2,
        recommended: 1,
        createdAt: "2026-10-01T10:00:00Z",
      })),
    ),
  })
  return renderWithProviders(
    <UploadGatewayProvider gateway={uploads}>
      <SearchGatewayProvider gateway={search}>
        <RecentPlaces />
      </SearchGatewayProvider>
    </UploadGatewayProvider>,
  )
}

describe("RecentPlaces", () => {
  it("links the latest files and the last search", async () => {
    renderRecent(5, 1)
    const section = await screen.findByRole("region", { name: en("recent.title") })
    const links = await within(section).findAllByRole("link")
    expect(links).toHaveLength(RECENT_FILES + 1)
    expect(links[0]).toHaveAttribute("href", "/uploads/u0")
    expect(links.at(-1)).toHaveAttribute("href", "/search/s0")
  })

  it("renders nothing without history", async () => {
    renderRecent(0, 0)
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(screen.queryByRole("region", { name: en("recent.title") })).toBeNull()
    expect(screen.queryByRole("link")).toBeNull()
  })
})
