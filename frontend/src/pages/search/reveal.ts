const shown = new Set<string>()

export function firstShow(searchId: string): boolean {
  if (shown.has(searchId)) return false
  shown.add(searchId)
  return true
}
