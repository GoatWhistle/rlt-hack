import { screen } from "@testing-library/react"
import { type RenderOptions, renderWithProviders } from "@tests/support/render"
import { Route, Routes, useNavigate } from "react-router"
import { ResultsPage } from "@/pages/results"

function Opener({ state }: { readonly state: unknown }) {
  const navigate = useNavigate()
  return (
    <button type="button" onClick={() => navigate("/results", { state })}>
      open
    </button>
  )
}

export async function openResults(state: unknown, options: RenderOptions = {}) {
  const view = renderWithProviders(
    <Routes>
      <Route path="/" element={<Opener state={state} />} />
      <Route path="/results" element={<ResultsPage />} />
    </Routes>,
    options,
  )
  await view.user.click(screen.getByRole("button", { name: "open" }))
  return view
}
