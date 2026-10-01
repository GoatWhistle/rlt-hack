import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { en, text } from "@tests/support/dictionaries"
import { createMemoryRouter } from "react-router"
import { describe, expect, it } from "vitest"
import { App } from "@/app/app"
import { createAppRouter, routes } from "@/app/router"

function renderApp(entries: string[] = ["/"]) {
  const router = createMemoryRouter(routes, {
    initialEntries: entries,
    initialIndex: entries.length - 1,
  })
  return { user: userEvent.setup(), router, ...render(<App router={router} />) }
}

describe("the application shell", () => {
  it("lazy-loads the home page inside the shell", async () => {
    renderApp()
    expect(
      await screen.findByRole("heading", { level: 1, name: en("intro.title", "uploads") }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("navigation", { name: en("app.mainNavigation") }),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: en("nav.uploads") })).toHaveAttribute(
      "aria-current",
      "page",
    )
    expect(screen.getByRole("link", { name: en("app.skipToContent") })).toHaveAttribute(
      "href",
      "#main-content",
    )
  })

  it("switches the whole interface to russian", async () => {
    const { user } = renderApp()
    await screen.findByRole("heading", { level: 1 })
    await user.click(screen.getByRole("radio", { name: en("language.ru") }))
    expect(
      await screen.findByRole("link", { name: text("ru", "common", "nav.uploads") }),
    ).toBeInTheDocument()
    expect(document.documentElement.lang).toBe("ru")
  })

  it("creates a browser router by default", () => {
    expect(createAppRouter().routes).toHaveLength(1)
  })
})

describe("the not found page", () => {
  it("answers an unknown address inside the shell with a way home", async () => {
    renderApp(["/missing/lot"])
    expect(
      await screen.findByRole("heading", { level: 1, name: en("notFound.title") }),
    ).toBeInTheDocument()
    expect(
      screen.getByText(en("errorDetails.code").replace("{{code}}", "http_404")),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: en("action.home") })).toHaveAttribute("href", "/")
    expect(screen.queryByRole("button", { name: en("action.back") })).not.toBeInTheDocument()
    expect(screen.getByRole("navigation")).toBeInTheDocument()
  })

  it("offers to go back when there is history", async () => {
    const { user, router } = renderApp(["/uploads", "/missing"])
    await user.click(await screen.findByRole("button", { name: en("action.back") }))
    expect(router.state.location.pathname).toBe("/uploads")
  })
})
