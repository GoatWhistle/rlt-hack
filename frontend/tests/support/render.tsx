import { QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactElement } from "react"
import { MemoryRouter } from "react-router"
import { createQueryClient } from "@/shared/api/query-client"
import type { Locale } from "@/shared/i18n/locale"
import { LocaleProvider } from "@/shared/i18n/locale-provider"
import { ToastProvider } from "@/shared/ui/toast"

export type RenderOptions = {
  readonly locale?: Locale
  readonly route?: string
}

export function renderWithProviders(ui: ReactElement, options: RenderOptions = {}) {
  const queryClient = createQueryClient()
  const user = userEvent.setup()
  const result = render(
    <LocaleProvider initialLocale={options.locale ?? "en"}>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <MemoryRouter initialEntries={[options.route ?? "/"]}>{ui}</MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    </LocaleProvider>,
  )
  return { ...result, user, queryClient }
}
