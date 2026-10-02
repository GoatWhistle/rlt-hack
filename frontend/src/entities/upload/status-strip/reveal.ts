const revealed = new Set<string>()

export function firstReveal(key: string): boolean {
  if (revealed.has(key)) return false
  revealed.add(key)
  return true
}
