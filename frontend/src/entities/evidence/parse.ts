import {
  count,
  type Fields,
  list,
  oneOf,
  optionalText,
  record,
  text,
  withOptional,
} from "@/shared/api/payload"
import {
  CHECK_REASONS,
  type CheckReason,
  type Contacts,
  HIGHLIGHT_CODES,
  type Highlight,
  SOURCE_KINDS,
  type Source,
} from "./model"

export function parseSource(value: unknown, path: string): Source | undefined {
  if (value === undefined || value === null) return undefined
  const fields = record(value, path)
  return withOptional(
    {
      kind: oneOf(SOURCE_KINDS, fields, "kind", path),
      title: text(fields, "title", path),
      url: text(fields, "url", path),
    },
    { checkedAt: optionalText(fields, "checkedAt", path) },
  )
}

function filled(fields: Readonly<Record<string, unknown>>, key: string, path: string) {
  const value = optionalText(fields, key, path)
  return value === "" ? undefined : value
}

export function parseContacts(value: unknown, path: string): Contacts | undefined {
  if (value === undefined || value === null) return undefined
  const fields = record(value, path)
  return withOptional(
    {},
    {
      site: filled(fields, "site", path),
      email: filled(fields, "email", path),
      phone: filled(fields, "phone", path),
    },
  )
}

export function parseHighlight(value: unknown, path: string): Highlight {
  const fields = record(value, path)
  const params = record(fields.params, `${path}.params`)
  return {
    code: oneOf(HIGHLIGHT_CODES, fields, "code", path),
    params: Object.fromEntries(
      Object.keys(params).map((key) => [key, count(params, key, `${path}.params`)]),
    ),
  }
}

export function parseHighlights(fields: Fields, path: string): Highlight[] {
  return list(fields, "highlights", path, parseHighlight)
}

export function parseCheckReasons(fields: Fields, path: string): CheckReason[] {
  return list(fields, "checkReasons", path, (entry, at) =>
    oneOf(CHECK_REASONS, { reason: entry }, "reason", at),
  )
}
