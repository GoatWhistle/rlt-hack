import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { en, text } from "@tests/support/dictionaries"
import { stubGateway } from "@tests/support/gateway"
import { chooseLanguage, LANGUAGE_TRIGGER } from "@tests/support/language"
import { createMemoryRouter } from "react-router"
import { describe, expect, it } from "vitest"
import { App } from "@/app/app"
import { createAppRouter, RouteLoading, routes } from "@/app/router"
import { UploadGatewayProvider } from "@/entities/upload/gateway-context"
import { LocaleProvider } from "@/shared/i18n/locale-provider"

function renderApp(entries: string[] = ["/"]) {
  const router = createMemoryRouter(routes, {
    initialEntries: entries,
    initialIndex: entries.length - 1,
  })
  return {
    user: userEvent.setup(),
    router,
    ...render(
      <UploadGatewayProvider gateway={stubGateway()}>
        <App router={router} />
      </UploadGatewayProvider>,
    ),
  }
}

describe("the application shell", () => {
  it("opens on the search, the main way in, inside the shell", async () => {
    const { router } = renderApp()
    expect(
      await screen.findByRole("heading", { level: 1, name: en("home.title", "search") }),
    ).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/search")
    const navigation = screen.getByRole("navigation", { name: en("app.mainNavigation") })
    const [first] = within(navigation).getAllByRole("link")
    expect(first).toHaveAccessibleName(en("nav.search"))
    expect(first).toHaveAttribute("aria-current", "page")
    await waitFor(() => expect(document.title).toBe("lotive | Search"))
    expect(screen.getByRole("link", { name: en("app.skipToContent") })).toHaveAttribute(
      "href",
      "#main-content",
    )
  })

  it("brands the header with the Lotive mark and name in every language", async () => {
    const { user } = renderApp()
    const brand = await screen.findByRole("link", { name: "lotive" })
    expect(brand).toHaveAttribute("href", "/search")
    expect(brand.querySelector("svg[aria-hidden='true']")).not.toBeNull()
    await chooseLanguage(user, "ru")
    expect(await screen.findByRole("link", { name: text("ru", "common", "app.name") })).toBe(
      brand,
    )
  })

  it("links to the repository in a new tab next to the language switch", async () => {
    renderApp()
    const repository = await screen.findByRole("link", { name: en("app.repository") })
    expect(repository).toHaveAttribute("href", "https://github.com/GoatWhistle/rlt-hack")
    expect(repository).toHaveAttribute("target", "_blank")
    expect(repository).toHaveAttribute("rel", "noopener noreferrer")
  })

  it("opens a language menu with flags from the globe and closes it after a choice", async () => {
    const { user } = renderApp()
    const trigger = await screen.findByRole("button", { name: LANGUAGE_TRIGGER })
    expect(trigger).toHaveAttribute("aria-haspopup", "menu")
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    await user.click(trigger)
    const menu = screen.getByRole("menu", { name: en("language.legend") })
    expect(trigger).toHaveAttribute("aria-expanded", "true")
    expect(menu.querySelectorAll("img[alt='']")).toHaveLength(2)
    expect(
      within(menu).getByRole("menuitemradio", { name: en("language.en") }),
    ).toHaveAttribute("aria-checked", "true")
    await user.click(within(menu).getByRole("menuitemradio", { name: en("language.ru") }))
    expect(
      within(menu).getByRole("menuitemradio", { name: en("language.ru") }),
    ).toHaveAttribute("aria-checked", "true")
    expect(menu).toHaveAttribute("data-indicator")
    await waitFor(() => expect(trigger).toHaveAttribute("aria-expanded", "false"))
    expect(trigger).toHaveFocus()
    expect(document.documentElement.lang).toBe("ru")
  })

  it("switches the whole interface to russian", async () => {
    const { user } = renderApp()
    await screen.findByRole("heading", { level: 1 })
    await chooseLanguage(user, "ru")
    expect(
      await screen.findByRole("link", { name: text("ru", "common", "nav.search") }),
    ).toBeInTheDocument()
    expect(document.documentElement.lang).toBe("ru")
  })

  it("draws a page skeleton while a route is loading", () => {
    render(
      <LocaleProvider initialLocale="en">
        <RouteLoading />
      </LocaleProvider>,
    )
    expect(screen.getByRole("status")).toHaveTextContent(en("state.loading"))
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
    expect(screen.queryByText(/http_404/)).not.toBeInTheDocument()
    expect(screen.getByRole("link", { name: en("action.newSearch") })).toHaveAttribute(
      "href",
      "/search",
    )
    expect(screen.getByRole("link", { name: en("action.home") })).toHaveAttribute(
      "href",
      "/history",
    )
    expect(screen.getByRole("navigation")).toBeInTheDocument()
    await waitFor(() => expect(document.title).toBe("lotive | Page not found"))
  })

  it("sends the old uploads address to the files history", async () => {
    renderApp(["/uploads"])
    await screen.findByRole("heading", { level: 1, name: en("title", "history") })
    await waitFor(() => expect(document.title).toBe("lotive | History"))
  })
})
