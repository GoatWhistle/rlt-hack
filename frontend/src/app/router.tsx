import { useTranslation } from "react-i18next"
import { createBrowserRouter, type RouteObject, redirect } from "react-router"
import { AppShell } from "@/app/app-shell"
import { NotFoundPage } from "@/pages/not-found"
import { RouteErrorPage } from "@/pages/route-error"
import { historyPath, SEARCH_PATH } from "@/shared/config/paths"
import { PageSkeleton } from "@/shared/ui/skeleton"
import { routeModules } from "./route-modules"

export function RouteLoading() {
  const { t } = useTranslation()
  return <PageSkeleton label={t("state.loading")} />
}

export function filesHistoryRedirect() {
  return redirect(historyPath("files"))
}

export const routes: RouteObject[] = [
  {
    path: "/",
    Component: AppShell,
    ErrorBoundary: RouteErrorPage,
    children: [
      {
        ErrorBoundary: RouteErrorPage,
        HydrateFallback: RouteLoading,
        children: [
          { index: true, loader: () => redirect(SEARCH_PATH), element: null },
          { path: "uploads", loader: filesHistoryRedirect, element: null },
          {
            path: "uploads/:uploadId",
            lazy: async () => ({ Component: (await routeModules.lots()).LotsPage }),
          },
          {
            path: "uploads/:uploadId/lots/:lotId",
            lazy: async () => ({ Component: (await routeModules.lot()).LotPage }),
          },
          {
            path: "uploads/:uploadId/lots/:lotId/evidence/:inn/:purchaseId",
            lazy: async () => ({
              Component: (await import("@/pages/procurement-source")).ProcurementSourcePage,
            }),
          },
          { path: "lots", loader: filesHistoryRedirect, element: null },
          {
            path: "history",
            lazy: async () => ({ Component: (await routeModules.history()).HistoryPage }),
          },
          {
            path: "search",
            lazy: async () => ({ Component: (await routeModules.search()).SearchPage }),
          },
          {
            path: "search/:searchId",
            lazy: async () => ({
              Component: (await routeModules.search()).SearchResultPage,
            }),
          },
          {
            path: "analytics",
            lazy: async () => ({ Component: (await routeModules.analytics()).AnalyticsLayout }),
            children: [
              {
                index: true,
                lazy: async () => ({
                  Component: (await routeModules.analytics()).OverviewPage,
                }),
              },
              {
                path: "categories/:code?",
                lazy: async () => ({
                  Component: (await routeModules.analytics()).CategoriesPage,
                }),
              },
              {
                path: "quality",
                lazy: async () => ({
                  Component: (await routeModules.analytics()).QualityPage,
                }),
              },
              {
                path: "sources",
                lazy: async () => ({
                  Component: (await routeModules.analytics()).SourcesPage,
                }),
              },
              {
                path: "records",
                lazy: async () => ({
                  Component: (await routeModules.analytics()).RecordsPage,
                }),
              },
            ],
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
