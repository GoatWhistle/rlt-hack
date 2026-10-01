import { type QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"
import { RouterProvider } from "react-router/dom"
import { AppErrorBoundary } from "@/app/error-boundary"
import { useMutationErrorToasts } from "@/app/mutation-error-toasts"
import { createAppRouter } from "@/app/router"
import { createQueryClient } from "@/shared/api/query-client"
import { LocaleProvider } from "@/shared/i18n/locale-provider"
import { ToastProvider } from "@/shared/ui/toast"

export type AppRouter = ReturnType<typeof createAppRouter>

export type AppProps = {
  readonly router?: AppRouter
  readonly queryClient?: QueryClient
}

function MutationErrorToasts({ queryClient }: { readonly queryClient: QueryClient }) {
  useMutationErrorToasts(queryClient)
  return null
}

export function App({ router, queryClient }: AppProps) {
  const [activeRouter] = useState(() => router ?? createAppRouter())
  const [activeClient] = useState(() => queryClient ?? createQueryClient())
  return (
    <LocaleProvider>
      <AppErrorBoundary>
        <QueryClientProvider client={activeClient}>
          <ToastProvider>
            <MutationErrorToasts queryClient={activeClient} />
            <RouterProvider router={activeRouter} />
          </ToastProvider>
        </QueryClientProvider>
      </AppErrorBoundary>
    </LocaleProvider>
  )
}
