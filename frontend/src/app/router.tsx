import { useTranslation } from "react-i18next"
import { createBrowserRouter, type RouteObject } from "react-router"
import { AppShell } from "@/app/app-shell"
import { NotFoundPage } from "@/pages/not-found"
import { RouteErrorPage } from "@/pages/route-error"
import { LoadingState } from "@/shared/ui/loading-state"

export function RouteLoading() {
  const { t } = useTranslation()
  return <LoadingState label={t("state.loading")} />
}

export const routes: RouteObject[] = [
  {
    path: "/",
    Component: AppShell,
    ErrorBoundary: RouteErrorPage,
    HydrateFallback: RouteLoading,
    children: [
      {
        ErrorBoundary: RouteErrorPage,
        children: [
          {
            index: true,
            lazy: async () => ({ Component: (await import("@/pages/upload")).UploadPage }),
          },
          {
            path: "results",
            lazy: async () => ({ Component: (await import("@/pages/results")).ResultsPage }),
          },
          { path: "*", Component: NotFoundPage },
        ],
      },
    ],
  },
]

export function createAppRouter() {
  return createBrowserRouter(routes)
}
