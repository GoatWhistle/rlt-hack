export const LOCALE_PART = 1

export function sameButLocale(
  previous: readonly unknown[] | undefined,
  next: readonly unknown[],
): boolean {
  if (!previous || previous.length !== next.length) return false
  return previous.every((part, index) => index === LOCALE_PART || part === next[index])
}

export function keptAcrossLocales<T>(key: readonly unknown[]) {
  return (
    previous: T | undefined,
    query: { readonly queryKey: readonly unknown[] } | undefined,
  ) => (sameButLocale(query?.queryKey, key) ? previous : undefined)
}
