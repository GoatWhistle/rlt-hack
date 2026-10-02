import { render, renderHook, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { text } from "@tests/support/dictionaries"
import { chooseLanguage, LANGUAGE_TRIGGER } from "@tests/support/language"
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
      {t("nav.history")}|{locale}|{money(1500)}
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
    expect(screen.getByTestId("probe")).toHaveTextContent(text("ru", "common", "nav.history"))
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
      `${text("en", "common", "nav.history")}|en`,
    )
    await chooseLanguage(user, "ru")
    expect(await screen.findByTestId("probe")).toHaveTextContent(
      `${text("ru", "common", "nav.history")}|ru`,
    )
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("ru")
    expect(document.documentElement.lang).toBe("ru")
    await user.click(screen.getByRole("button", { name: LANGUAGE_TRIGGER }))
    expect(
      screen.getByRole("menuitemradio", { name: text("ru", "common", "language.ru") }),
    ).toHaveAttribute("aria-checked", "true")
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
    expect(en.dateTime(new Date(2025, 0, 2, 15, 4))).toBe("Jan 2, 2025, 3:04 PM")
    expect(ru.dateTime("2025-01-02T12:00:00")).toMatch(/^2 янв\. 2025 г\., 12:00$/u)
  })

  it("join lists the way each language does", () => {
    expect(createFormatters("en").list(["Rice", "Sugar", "Tea"])).toBe("Rice, Sugar, and Tea")
    expect(createFormatters("ru").list(["Рис", "Сахар", "Чай"])).toBe("Рис, Сахар и Чай")
    expect(createFormatters("en").list(["Rice"])).toBe("Rice")
  })

  it("build each locale's formatters once", () => {
    expect(createFormatters("en")).toBe(createFormatters("en"))
    expect(createFormatters("en").money(1, "USD")).toBe(createFormatters("en").money(1, "USD"))
  })
})
