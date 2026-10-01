import { afterEach, describe, expect, it, vi } from "vitest"
import { currentLocale, i18n, initI18n } from "@/shared/i18n/i18n"
import {
  DEFAULT_LOCALE,
  isLocale,
  LOCALE_STORAGE_KEY,
  navigatorLocale,
  readStoredLocale,
  resolveLocale,
  toLocale,
  writeStoredLocale,
} from "@/shared/i18n/locale"

afterEach(() => {
  vi.restoreAllMocks()
})

describe("locale parsing", () => {
  it("accepts only supported locales", () => {
    expect([isLocale("ru"), isLocale("en"), isLocale("de"), isLocale(1)]).toEqual([
      true,
      true,
      false,
      false,
    ])
  })

  it("reduces language tags to a supported base", () => {
    expect([toLocale("en-GB"), toLocale("RU"), toLocale("de-DE"), toLocale(null)]).toEqual([
      "en",
      "ru",
      null,
      null,
    ])
  })
})

describe("locale storage", () => {
  it("round-trips the chosen locale", () => {
    writeStoredLocale("en")
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("en")
    expect(readStoredLocale()).toBe("en")
  })

  it("survives a storage that throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied")
    })
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("denied")
    })
    expect(() => writeStoredLocale("ru")).not.toThrow()
    expect(readStoredLocale()).toBeNull()
  })
})

describe("locale resolution", () => {
  it("prefers storage, then the browser, then the default", () => {
    const languages = vi.spyOn(navigator, "languages", "get")
    languages.mockReturnValue(["de-DE", "en-US"])
    expect(navigatorLocale()).toBe("en")
    writeStoredLocale("ru")
    expect(resolveLocale()).toBe("ru")
    localStorage.clear()
    expect(resolveLocale()).toBe("en")
    languages.mockReturnValue(["de-DE"])
    expect(resolveLocale()).toBe(DEFAULT_LOCALE)
  })

  it("falls back to navigator.language when the list is empty", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue([])
    vi.spyOn(navigator, "language", "get").mockReturnValue("ru-RU")
    expect(navigatorLocale()).toBe("ru")
  })
})

describe("i18n instance", () => {
  it("switches language when initialised again", async () => {
    initI18n("ru")
    await vi.waitFor(() => expect(currentLocale()).toBe("ru"))
    expect(i18n.t("nav.uploads")).not.toBe("nav.uploads")
    initI18n("en")
    await vi.waitFor(() => expect(currentLocale()).toBe("en"))
  })
})
