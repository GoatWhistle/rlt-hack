import {
  count,
  type Fields,
  knownList,
  knownOf,
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
  type SearchWarning,
  SOURCE_KINDS,
  type Source,
  WARNING_CODES,
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

export function parseHighlight(value: unknown, path: string): Highlight | undefined {
  const fields = record(value, path)
  const params = record(fields.params, `${path}.params`)
  const code = knownOf(HIGHLIGHT_CODES, fields.code, `${path}.code`)
  if (code === undefined) return undefined
  return {
    code,
    params: Object.fromEntries(
      Object.keys(params).map((key) => [key, count(params, key, `${path}.params`)]),
    ),
  }
}

export function parseHighlights(fields: Fields, path: string): Highlight[] {
  return knownList(fields, "highlights", path, parseHighlight)
}

export function parseCheckReasons(fields: Fields, path: string): CheckReason[] {
  return knownList(fields, "checkReasons", path, (entry, at) =>
    knownOf(CHECK_REASONS, entry, at),
  )
}

export function parseWarnings(fields: Fields, path: string): SearchWarning[] {
  return knownList(fields, "warnings", path, (entry, at) => {
    const warning = record(entry, at)
    const code = knownOf(WARNING_CODES, warning.code, `${at}.code`)
    return code === undefined
      ? undefined
      : { code, subject: optionalText(warning, "subject", at) ?? "" }
  })
}
