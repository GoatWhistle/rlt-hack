import { render, renderHook, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { text } from "@tests/support/dictionaries"
import { useTranslation } from "react-i18next"
import { describe, expect, it } from "vitest"
import { LocaleSwitch } from "@/features/locale-switch"
import { createFormatters, useFormatters } from "@/shared/i18n/formatters"
import { LOCALE_STORAGE_KEY } from "@/shared/i18n/locale"
import { LocaleProvider, useLocale } from "@/shared/i18n/locale-provider"

function Probe() {
  const { t } = useTranslation()
  const { locale } = useLocale()
  const { money } = useFormatters()
  return (
    <p data-testid="probe">
      {t("nav.home")}|{locale}|{money(1500)}
    </p>
  )
}

describe("locale provider", () => {
  it("renders the stored language first and sets the document language", () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, "ru")
    render(
      <LocaleProvider>
        <Probe />
      </LocaleProvider>,
    )
    expect(screen.getByTestId("probe")).toHaveTextContent(text("ru", "common", "nav.home"))
    expect(document.documentElement.lang).toBe("ru")
  })

  it("re-translates and persists after a switch", async () => {
    const user = userEvent.setup()
    render(
      <LocaleProvider initialLocale="en">
        <LocaleSwitch />
        <Probe />
      </LocaleProvider>,
    )
    expect(screen.getByTestId("probe")).toHaveTextContent(
      `${text("en", "common", "nav.home")}|en`,
    )
    await user.click(screen.getByRole("radio", { name: text("en", "common", "language.ru") }))
    expect(await screen.findByTestId("probe")).toHaveTextContent(
      `${text("ru", "common", "nav.home")}|ru`,
    )
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("ru")
    expect(document.documentElement.lang).toBe("ru")
    expect(
      screen.getByRole("radio", { name: text("ru", "common", "language.ru") }),
    ).toBeChecked()
  })

  it("refuses to be used without a provider", () => {
    expect(() => renderHook(() => useLocale())).toThrow(
      "useLocale must be used within LocaleProvider",
    )
  })
})

describe("formatters", () => {
  it("format numbers, money and dates per locale", () => {
    const ru = createFormatters("ru")
    const en = createFormatters("en")
    expect(en.number(1234.5)).toBe("1,234.5")
    expect(ru.number(1234.5)).toMatch(/^1\s234,5$/u)
    expect(en.money(10, "USD")).toBe("$10.00")
    expect(ru.money(10)).toContain("₽")
    expect(en.date("2025-03-01T00:00:00Z")).toBe("Mar 1, 2025")
    expect(en.date(new Date(Date.UTC(2025, 0, 2)))).toBe("Jan 2, 2025")
  })
})
