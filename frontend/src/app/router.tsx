import { useTranslation } from "react-i18next"
import { createBrowserRouter, type RouteObject, redirect } from "react-router"
import { AppShell } from "@/app/app-shell"
import { readLastUpload } from "@/entities/upload/last-upload"
import { NotFoundPage } from "@/pages/not-found"
import { RouteErrorPage } from "@/pages/route-error"
import { UPLOADS_PATH, uploadPath } from "@/shared/config/paths"
import { PageSkeleton } from "@/shared/ui/skeleton"

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
          { index: true, loader: () => redirect(UPLOADS_PATH), element: null },
          {
            path: "uploads",
            lazy: async () => ({ Component: (await import("@/pages/uploads")).UploadsPage }),
          },
          {
            path: "uploads/:uploadId",
            lazy: async () => ({ Component: (await import("@/pages/lots")).LotsPage }),
          },
          {
            path: "uploads/:uploadId/lots/:lotId",
            lazy: async () => ({ Component: (await import("@/pages/lot")).LotPage }),
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
              Component: (await import("@/pages/lots-entry")).LotsEntryPage,
            }),
          },
          {
            path: "search",
            lazy: async () => ({ Component: (await import("@/pages/search")).SearchPage }),
          },
          {
            path: "search/:searchId",
            lazy: async () => ({
              Component: (await import("@/pages/search")).SearchResultPage,
            }),
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
