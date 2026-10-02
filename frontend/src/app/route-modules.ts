export const routeModules = {
  lots: () => import("@/pages/lots"),
  lot: () => import("@/pages/lot"),
  search: () => import("@/pages/search"),
  analytics: () => import("@/pages/analytics"),
  history: () => import("@/pages/history"),
} as const

export type RouteModule = keyof typeof routeModules

export function preload(module: RouteModule): void {
  void routeModules[module]().catch(() => undefined)
}
