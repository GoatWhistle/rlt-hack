import type {
  ComboboxGroup,
  ComboboxItem,
  ComboboxOption,
  ComboboxSection,
  TextRange,
} from "./model"

const DIAERESIS = /\u0308/g
const DASHES = /[-\u2010-\u2015]/g
const RESULTS = "results"

export function fold(text: string, locale: string): string {
  return text
    .toLocaleLowerCase(locale)
    .normalize("NFD")
    .replace(DIAERESIS, "")
    .normalize("NFC")
    .replace(DASHES, " ")
}

type Hit = { readonly at: number; readonly wordStart: boolean }

function find(text: string, query: string): Hit | null {
  let first: Hit | null = null
  let from = 0
  for (;;) {
    const at = text.indexOf(query, from)
    if (at < 0) return first
    const wordStart = at === 0 || text[at - 1] === " "
    if (wordStart) return { at, wordStart }
    first ??= { at, wordStart }
    from = at + 1
  }
}

function grade(hit: Hit | null, start: number, word: number, inside: number): number {
  if (!hit) return Number.POSITIVE_INFINITY
  if (hit.at === 0) return start
  return hit.wordStart ? word : inside
}

function rangeOf(hit: Hit | null, length: number): TextRange | undefined {
  return hit ? [hit.at, hit.at + length] : undefined
}

export type Ranked = { readonly item: ComboboxItem; readonly score: number }

export function rank(option: ComboboxOption, query: string, locale: string): Ranked | null {
  const label = find(fold(option.label, locale), query)
  const detail = option.detail ? find(fold(option.detail, locale), query) : null
  const keyword = Math.min(
    ...(option.keywords ?? []).map((word) => grade(find(fold(word, locale), query), 1, 3, 5)),
  )
  const score = Math.min(grade(label, 0, 2, 4), keyword, grade(detail, 6, 6, 7))
  if (!Number.isFinite(score)) return null
  return {
    score,
    item: {
      option,
      label: rangeOf(label, query.length),
      detail: rangeOf(detail, query.length),
    },
  }
}

export function search(
  groups: readonly ComboboxGroup[],
  query: string,
  locale: string,
): readonly ComboboxItem[] {
  const needle = fold(query.trim(), locale)
  const seen = new Set<string>()
  return groups
    .flatMap((group) => group.options)
    .map((option, order) => ({ order, found: rank(option, needle, locale) }))
    .filter((entry): entry is { order: number; found: Ranked } => entry.found !== null)
    .sort((a, b) => a.found.score - b.found.score || a.order - b.order)
    .map(({ found }) => found.item)
    .filter(({ option }) => {
      if (seen.has(option.value)) return false
      seen.add(option.value)
      return true
    })
}

export function sectionsFor(
  groups: readonly ComboboxGroup[],
  query: string,
  locale: string,
): readonly ComboboxSection[] {
  if (query.trim() === "") {
    return groups.map((group) => ({
      key: group.key,
      label: group.label,
      items: group.options.map((option) => ({ option })),
    }))
  }
  const items = search(groups, query, locale)
  return items.length > 0 ? [{ key: RESULTS, items }] : []
}
