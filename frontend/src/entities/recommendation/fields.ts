export class RecommendationFormatError extends Error {
  constructor(path: string) {
    super(`unexpected recommendation payload at ${path}`)
    this.name = "RecommendationFormatError"
  }
}

export type Fields = Readonly<Record<string, unknown>>

export function record(value: unknown, path: string): Fields {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new RecommendationFormatError(path)
  }
  return value as Fields
}

export function text(fields: Fields, key: string, path: string): string {
  const value = fields[key]
  if (typeof value !== "string") throw new RecommendationFormatError(`${path}.${key}`)
  return value
}

export function optionalText(fields: Fields, key: string, path: string): string | undefined {
  return fields[key] === undefined || fields[key] === null ? undefined : text(fields, key, path)
}

export function count(fields: Fields, key: string, path: string): number {
  const value = fields[key]
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new RecommendationFormatError(`${path}.${key}`)
  }
  return value
}

export function list<T>(
  fields: Fields,
  key: string,
  path: string,
  item: (value: unknown, at: string) => T,
): T[] {
  const value = fields[key]
  if (!Array.isArray(value)) throw new RecommendationFormatError(`${path}.${key}`)
  return value.map((entry, index) => item(entry, `${path}.${key}[${index}]`))
}

export function oneOf<T extends string>(
  options: readonly T[],
  fields: Fields,
  key: string,
  path: string,
): T {
  const value = text(fields, key, path)
  const found = options.find((option) => option === value)
  if (!found) throw new RecommendationFormatError(`${path}.${key}`)
  return found
}

export function plainText(value: unknown, path: string): string {
  if (typeof value !== "string") throw new RecommendationFormatError(path)
  return value
}

export function withOptional<T extends object>(base: T, extra: Record<string, unknown>): T {
  const defined = Object.entries(extra).filter(([, value]) => value !== undefined)
  return { ...base, ...Object.fromEntries(defined) }
}
