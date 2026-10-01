import { render, screen } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { describe, expect, it, vi } from "vitest"
import { ApiError } from "@/shared/api/api-error"
import { Button, ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { LoadingState } from "@/shared/ui/loading-state"
import { SegmentedControl } from "@/shared/ui/segmented-control"
import { SkipLink } from "@/shared/ui/skip-link"

describe("Button", () => {
  it("defaults to a non-submitting button and keeps extra classes", () => {
    render(<Button className="extra">save</Button>)
    const button = screen.getByRole("button", { name: "save" })
    expect(button).toHaveAttribute("type", "button")
    expect(button.className).toContain("extra")
  })

  it("renders a link that looks like a button", () => {
    renderWithProviders(
      <ButtonLink to="/lots" variant="secondary">
        lots
      </ButtonLink>,
    )
    expect(screen.getByRole("link", { name: "lots" })).toHaveAttribute("href", "/lots")
  })
})

describe("SegmentedControl", () => {
  it("is a labelled radio group that reports the chosen value", async () => {
    const onChange = vi.fn()
    const { user } = renderWithProviders(
      <SegmentedControl
        legend="View"
        value="grid"
        onChange={onChange}
        options={[
          { value: "grid", label: "G", description: "Grid" },
          { value: "list", label: "List" },
        ]}
      />,
    )
    expect(screen.getByRole("group", { name: "View" })).toBeInTheDocument()
    expect(screen.getByRole("radio", { name: "Grid" })).toBeChecked()
    await user.click(screen.getByRole("radio", { name: "List" }))
    expect(onChange).toHaveBeenCalledWith("list")
  })
})

describe("EmptyState", () => {
  it("renders an optional description, details and actions", () => {
    render(
      <EmptyState
        title="Nothing"
        headingLevel={2}
        description="d"
        details="x"
        actions={<b>a</b>}
      />,
    )
    expect(screen.getByRole("heading", { level: 2, name: "Nothing" })).toBeInTheDocument()
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    expect(screen.getByText("x")).toBeInTheDocument()
  })
})

describe("ErrorState", () => {
  it("explains the error, shows its code and retries", async () => {
    const onRetry = vi.fn()
    const { user } = renderWithProviders(
      <ErrorState error={new ApiError({ status: 0, code: "network" })} onRetry={onRetry} />,
    )
    const alert = screen.getByRole("alert")
    expect(alert).toHaveTextContent(en("network", "errors"))
    expect(alert).toHaveTextContent("network")
    await user.click(screen.getByRole("button", { name: en("action.retry") }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it("works without a code or actions", () => {
    renderWithProviders(<ErrorState error={new Error("x")} title="Lots" />)
    expect(screen.getByRole("heading", { level: 2, name: "Lots" })).toBeInTheDocument()
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
  })
})

describe("small primitives", () => {
  it("expose a skip link and a busy status", () => {
    render(
      <>
        <SkipLink targetId="main" label="Skip" />
        <LoadingState label="Loading" />
      </>,
    )
    expect(screen.getByRole("link", { name: "Skip" })).toHaveAttribute("href", "#main")
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true")
    expect(screen.getByRole("status")).toHaveTextContent("Loading")
  })
})
