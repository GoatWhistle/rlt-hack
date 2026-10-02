export const routeModules = {
  uploads: () => import("@/pages/uploads"),
  lots: () => import("@/pages/lots"),
  lot: () => import("@/pages/lot"),
  lotsEntry: () => import("@/pages/lots-entry"),
  search: () => import("@/pages/search"),
  analytics: () => import("@/pages/analytics"),
} as const

export type RouteModule = keyof typeof routeModules

export function preload(module: RouteModule): void {
  void routeModules[module]().catch(() => undefined)
}
