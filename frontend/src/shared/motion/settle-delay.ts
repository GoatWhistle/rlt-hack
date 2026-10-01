export const SETTLE_MS = 220

export function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false
}

export function settleDelay(): number {
  return prefersReducedMotion() ? 0 : SETTLE_MS
}
