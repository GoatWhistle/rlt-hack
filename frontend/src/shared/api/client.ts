import { env } from "@/shared/config/env"
import { currentLocale } from "@/shared/i18n/i18n"
import { LOCALE_TAGS } from "@/shared/i18n/locale"
import { createHttpClient } from "./http-client"

export const apiClient = createHttpClient({
  baseUrl: env.apiBaseUrl,
  language: () => LOCALE_TAGS[currentLocale()],
})
