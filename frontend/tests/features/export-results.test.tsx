import { screen, waitFor } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { lotSummary, stubGateway } from "@tests/support/gateway"
import { renderWithProviders } from "@tests/support/render"
import { afterEach, describe, expect, it, vi } from "vitest"
import { resetShortlists, toggleShortlisted } from "@/entities/shortlist/store"
import { UploadGatewayProvider } from "@/entities/upload/gateway-context"
import type { LotResult } from "@/entities/upload/model"
import { ExportDialog, type ExportDialogProps } from "@/features/export-results"
import {
  CSV_BOM,
  CSV_TYPE,
  exportFileNames,
  productsCsv,
  suppliersCsv,
  toCsv,
} from "@/features/export-results/csv"
import * as download from "@/shared/download/save-text-file"
import { recommendationFixture } from "../entities/recommendation/fixture"

const results: LotResult[] = [
  { lot: lotSummary("10"), recommendation: recommendationFixture },
  { lot: lotSummary("11", { status: "queued" }) },
]

afterEach(() => {
  vi.restoreAllMocks()
  resetShortlists()
})

describe("the result files", () => {
  it("link products and suppliers to the source lot", () => {
    const products = productsCsv(results)
    expect(products.startsWith(CSV_BOM)).toBe(true)
    expect(products).toContain("lot_id;product_name;okpd2_code;origin\r\n")
    expect(products).toContain("10;Sugar;10.81.12;inferred\r\n")
    const suppliers = suppliersCsv(results)
    expect(suppliers).toContain(
      "10;1;7800000011;North Foods;Supplier;recommended;;5;5;1;3;1;11;4;",
    )
    expect(suppliers).toContain("10;3;7800000033;West Trade;Distributor;check;;1;5;0;1;0;3;0;")
    const chosen = suppliersCsv(results, { "10": ["west"] })
    expect(chosen).not.toContain("North Foods")
    expect(chosen).toContain("West Trade")
  })

  it("keeps spreadsheet formulas from running", () => {
    expect(
      toCsv(
        ["a", "b"],
        [
          ["=HYPERLINK(1)", -5],
          ["@cmd", "+1"],
        ],
      ),
    ).toBe(`${CSV_BOM}a;b\r\n'=HYPERLINK(1);-5\r\n'@cmd;'+1\r\n`)
  })

  it("quotes cells that need it and names the files after the upload", () => {
    expect(toCsv(["a"], [['say "hi"; ok']])).toBe(`${CSV_BOM}a\r\n"say ""hi""; ok"\r\n`)
    expect(exportFileNames("notices.csv")).toEqual({
      products: "notices-products.csv",
      suppliers: "notices-suppliers.csv",
    })
    expect(exportFileNames(".csv").products).toBe("results-products.csv")
  })
})

function openDialog(props: Partial<ExportDialogProps>, gateway = stubGateway()) {
  const onClose = vi.fn()
  const view = renderWithProviders(
    <UploadGatewayProvider gateway={gateway}>
      <ExportDialog
        open
        onClose={onClose}
        uploadId="u1"
        fileName="notices.csv"
        lots={[lotSummary("10"), lotSummary("11", { status: "queued" }), lotSummary("12")]}
        {...props}
      />
    </UploadGatewayProvider>,
  )
  return { ...view, onClose, gateway }
}

describe("the export dialog", () => {
  it("explains the scope and downloads two files for finished purchases", async () => {
    const save = vi.spyOn(download, "saveTextFile").mockImplementation(() => {})
    const gateway = stubGateway({ results: vi.fn(async () => results) })
    const { user, onClose } = openDialog({}, gateway)
    expect(screen.getByRole("radio", { name: "All purchases in the file (3)" })).toBeChecked()
    expect(
      screen.getByText(/2 purchases with a finished result are included\./),
    ).toBeInTheDocument()
    expect(screen.getByText(/1 more is still processing/)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: en("submit", "export") }))
    await waitFor(() => expect(onClose).toHaveBeenCalled())
    expect(screen.getAllByText(en("done", "export")).length).toBeGreaterThan(0)
    expect(gateway.results).toHaveBeenCalledWith("u1", ["10", "12"])
    expect(save.mock.calls.map(([name, , type]) => [name, type])).toEqual([
      ["notices-products.csv", CSV_TYPE],
      ["notices-suppliers.csv", CSV_TYPE],
    ])
  })

  it("narrows to this purchase or the selection and to chosen candidates", async () => {
    vi.spyOn(download, "saveTextFile").mockImplementation(() => {})
    toggleShortlisted("u1", "10", "west")
    const gateway = stubGateway({ results: vi.fn(async () => results) })
    const { user } = openDialog({ currentLotId: "10", selectedIds: ["10", "12"] }, gateway)
    expect(screen.getByRole("radio", { name: en("lots.lot", "export") })).toBeChecked()
    expect(screen.getByRole("radio", { name: "Only the ones you chose (1)" })).toBeChecked()
    await user.click(screen.getByRole("radio", { name: "Selected (2)" }))
    expect(screen.getByRole("radio", { name: "Only the ones you chose (1)" })).toBeChecked()
    await user.click(screen.getByRole("radio", { name: en("candidates.all", "export") }))
    await user.click(screen.getByRole("radio", { name: "Only the ones you chose (1)" }))
    await user.click(screen.getByRole("button", { name: en("submit", "export") }))
    await waitFor(() => expect(gateway.results).toHaveBeenCalledWith("u1", ["10", "12"]))
  })

  it("leaves out purchases that could not be processed", async () => {
    openDialog({ lots: [lotSummary("10"), lotSummary("13", { status: "failed" })] })
    expect(
      screen.getByText(/1 purchase with a finished result is included\./),
    ).toBeInTheDocument()
    expect(screen.queryByText(/still processing/)).toBeNull()
  })

  it("writes the summary of each company", async () => {
    const save = vi.spyOn(download, "saveTextFile").mockImplementation(() => {})
    const gateway = stubGateway({ results: vi.fn(async () => results) })
    const { user, onClose } = openDialog({ currentLotId: "10" }, gateway)
    await user.click(screen.getByRole("button", { name: en("submit", "export") }))
    await waitFor(() => expect(onClose).toHaveBeenCalled())
    const suppliers = String(save.mock.calls[1]?.[1])
    expect(suppliers).toContain(recommendationFixture.companies[0]?.summary ?? "")
  })

  it("warns when nothing is ready or nothing was chosen, and reports failures", async () => {
    const gateway = stubGateway({
      results: vi.fn(async () => {
        throw new Error("down")
      }),
    })
    const { user } = openDialog({ currentLotId: "11" }, gateway)
    expect(
      screen.getByText((content) => content.startsWith(en("nothing", "export"))),
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: en("submit", "export") })).toBeDisabled()
    await user.click(screen.getByRole("radio", { name: "All purchases in the file (3)" }))
    const shortlist = screen.getByRole("radio", { name: "Only the ones you chose (0)" })
    expect(shortlist).toBeDisabled()
    expect(shortlist).toHaveAccessibleDescription(en("noShortlist", "export"))
    expect(screen.getByRole("radio", { name: en("candidates.all", "export") })).toBeChecked()
    await user.click(screen.getByRole("button", { name: en("submit", "export") }))
    expect(await screen.findByRole("alert")).toHaveTextContent(en("failed", "export"))
  })
})
