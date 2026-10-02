import { useTranslation } from "react-i18next"
import { createBrowserRouter, type RouteObject, redirect } from "react-router"
import { AppShell } from "@/app/app-shell"
import { readLastUpload } from "@/entities/upload/last-upload"
import { NotFoundPage } from "@/pages/not-found"
import { RouteErrorPage } from "@/pages/route-error"
import { SEARCH_PATH, uploadPath } from "@/shared/config/paths"
import { PageSkeleton } from "@/shared/ui/skeleton"
import { routeModules } from "./route-modules"

export function RouteLoading() {
  const { t } = useTranslation()
  return <PageSkeleton label={t("state.loading")} />
}

export function lastUploadRedirect() {
  const uploadId = readLastUpload()
  return uploadId ? redirect(uploadPath(uploadId)) : null
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
          {
            path: "uploads",
            lazy: async () => ({ Component: (await routeModules.uploads()).UploadsPage }),
          },
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
          {
            path: "lots",
            loader: lastUploadRedirect,
            lazy: async () => ({
              Component: (await routeModules.lotsEntry()).LotsEntryPage,
            }),
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
