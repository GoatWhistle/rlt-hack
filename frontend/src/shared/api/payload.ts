export class PayloadFormatError extends Error {
  constructor(path: string) {
    super(`unexpected payload at ${path}`)
    this.name = "PayloadFormatError"
  }
}

export type Fields = Readonly<Record<string, unknown>>

function absent(value: unknown): boolean {
  return value === undefined || value === null
}

export function record(value: unknown, path: string): Fields {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new PayloadFormatError(path)
  }
  return value as Fields
}

export function text(fields: Fields, key: string, path: string): string {
  const value = fields[key]
  if (typeof value !== "string") throw new PayloadFormatError(`${path}.${key}`)
  return value
}

export function optionalText(fields: Fields, key: string, path: string): string | undefined {
  return absent(fields[key]) ? undefined : text(fields, key, path)
}

export function count(fields: Fields, key: string, path: string): number {
  const value = fields[key]
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new PayloadFormatError(`${path}.${key}`)
  }
  return value
}

export function optionalAmount(fields: Fields, key: string, path: string): number | undefined {
  const value = fields[key]
  if (absent(value)) return undefined
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    throw new PayloadFormatError(`${path}.${key}`)
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
  if (!Array.isArray(value)) throw new PayloadFormatError(`${path}.${key}`)
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
  if (!found) throw new PayloadFormatError(`${path}.${key}`)
  return found
}

export function plainText(value: unknown, path: string): string {
  if (typeof value !== "string") throw new PayloadFormatError(path)
  return value
}

export function withOptional<T extends object>(base: T, extra: Record<string, unknown>): T {
  const defined = Object.entries(extra).filter(([, value]) => value !== undefined)
  return { ...base, ...Object.fromEntries(defined) }
}
