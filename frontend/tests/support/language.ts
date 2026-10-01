import { screen, waitFor } from "@testing-library/react"
import type { UserEvent } from "@testing-library/user-event"
import { expect } from "vitest"
import type { Locale } from "@/shared/i18n/locale"
import { text } from "./dictionaries"

export const LANGUAGE_TRIGGER = /^(language|язык): /i

export async function chooseLanguage(user: UserEvent, locale: Locale): Promise<void> {
  const trigger = screen.getByRole("button", { name: LANGUAGE_TRIGGER })
  await user.click(trigger)
  await user.click(
    await screen.findByRole("menuitemradio", {
      name: text(locale, "common", `language.${locale}`),
    }),
  )
  await waitFor(() => expect(trigger).toHaveAttribute("aria-expanded", "false"))
}
