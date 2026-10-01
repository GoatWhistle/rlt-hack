export const FALLBACK_ITEM_LIMIT = 8
export const ITEM_NAME_LIMIT = 120

const SEPARATOR = /[;\n]+/
const TRAILING_QUANTITY = /^(.*?\p{L}.*?)[\s,:-]+(\d+(?:[.,]\d+)?)\s*(\p{L}{1,8}\.?)?$/u

export type FallbackItem = {
  readonly id: string
  readonly name: string
  readonly okpd2: string
  readonly itemType: "unknown"
  readonly origin: "text"
  readonly quantity: { readonly value: string; readonly unit: string } | null
}

function item(segment: string, index: number): FallbackItem {
  const found = TRAILING_QUANTITY.exec(segment)
  const name = (found?.[1] ?? segment).slice(0, ITEM_NAME_LIMIT)
  return {
    id: `i${index + 1}`,
    name,
    okpd2: "",
    itemType: "unknown",
    origin: "text",
    quantity: found?.[2]
      ? { value: found[2].replace(",", "."), unit: found[3]?.replace(/\.$/, "") ?? "" }
      : null,
  }
}

export function fallbackItems(text: string): FallbackItem[] {
  return text
    .split(SEPARATOR)
    .map((segment) => segment.trim())
    .filter((segment) => segment.length > 0)
    .slice(0, FALLBACK_ITEM_LIMIT)
    .map(item)
}
