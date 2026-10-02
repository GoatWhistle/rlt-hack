import {
  count,
  list,
  oneOf,
  optionalOneOf,
  optionalText,
  plainText,
  record,
  text,
  withOptional,
} from "@/shared/api/payload"
import { LOCALES } from "@/shared/i18n/locale"
import {
  FILTER_ITEM_TYPES,
  SEARCH_ORIGINS,
  type SearchContext,
  type SearchFilters,
  type SearchQuery,
} from "./model"

function filters(value: unknown, path: string): SearchFilters {
  if (value === undefined || value === null) return {}
  const fields = record(value, path)
  return withOptional(
    {},
    {
      regions:
        fields.regions === undefined || fields.regions === null
          ? undefined
          : list(fields, "regions", path, plainText),
      itemType: optionalOneOf(FILTER_ITEM_TYPES, fields, "itemType", path),
    },
  )
}

function context(value: unknown, path: string): SearchContext {
  if (value === undefined || value === null) return {}
  const fields = record(value, path)
  return withOptional(
    {},
    {
      customerInn: optionalText(fields, "customerInn", path),
      startPrice: optionalText(fields, "startPrice", path),
    },
  )
}

export function parseQuery(value: unknown, path: string): SearchQuery {
  const fields = record(value, path)
  return {
    text: text(fields, "text", path),
    locale: oneOf(LOCALES, fields, "locale", path),
    limit: count(fields, "limit", path),
    filters: filters(fields.filters, `${path}.filters`),
    context: context(fields.context, `${path}.context`),
    origin: optionalOneOf(SEARCH_ORIGINS, fields, "origin", path) ?? "manual",
  }
}
