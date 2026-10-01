import { fireEvent, screen } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { Route, Routes, useLocation } from "react-router"
import { describe, expect, it } from "vitest"
import { RESULTS_PATH, UploadPage } from "@/pages/upload"

function ResultsProbe() {
  const location = useLocation()
  const state = location.state as { fileName?: string } | null
  return <output>{state?.fileName}</output>
}

function renderUpload() {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<UploadPage />} />
      <Route path={RESULTS_PATH} element={<ResultsProbe />} />
    </Routes>,
  )
}

const file = new File(["x".repeat(2048)], "lot.xlsx")

describe("the upload page", () => {
  it("explains the four steps of the reasoning", () => {
    renderUpload()
    expect(
      screen.getByRole("heading", { level: 1, name: en("upload.title") }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("heading", { level: 3, name: en("upload.steps.evidence.title") }),
    ).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: en("upload.submit") })).not.toBeInTheDocument()
  })

  it("sends the chosen file and opens its result", async () => {
    const { user } = renderUpload()
    await user.upload(screen.getByLabelText(en("upload.chooseFile")), file)
    expect(screen.getByText("lot.xlsx")).toBeInTheDocument()
    expect(screen.getByText("2 KB · ready to process")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: en("upload.submit") }))
    expect(screen.getByRole("button", { name: en("upload.submitting") })).toBeDisabled()
    expect(await screen.findByRole("status")).toHaveTextContent("lot.xlsx")
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument()
  })

  it("takes a file dropped onto the zone", () => {
    renderUpload()
    const zone = screen.getByRole("region", { name: en("upload.dropTitle") })
    fireEvent.dragOver(zone, { dataTransfer: { files: [] } })
    fireEvent.dragLeave(zone)
    fireEvent.drop(zone, { dataTransfer: { files: [] } })
    expect(screen.queryByText("lot.xlsx")).not.toBeInTheDocument()
    fireEvent.drop(zone, { dataTransfer: { files: [file] } })
    expect(screen.getByText("lot.xlsx")).toBeInTheDocument()
  })
})
