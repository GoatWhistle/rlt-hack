import i18next from "i18next"
import { initReactI18next } from "react-i18next"
import { DEFAULT_LOCALE, LOCALES, type Locale, toLocale } from "./locale"
import { DEFAULT_NAMESPACE, NAMESPACES, resources } from "./resources"

export const i18n = i18next.createInstance()

export function initI18n(locale: Locale): typeof i18n {
  if (i18n.isInitialized) {
    if (i18n.language !== locale) void i18n.changeLanguage(locale)
    return i18n
  }
  void i18n.use(initReactI18next).init({
    resources,
    lng: locale,
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: LOCALES,
    ns: NAMESPACES,
    defaultNS: DEFAULT_NAMESPACE,
    interpolation: { escapeValue: false },
    returnNull: false,
    initAsync: false,
  })
  return i18n
}

export function currentLocale(): Locale {
  return toLocale(i18n.language) ?? DEFAULT_LOCALE
}
