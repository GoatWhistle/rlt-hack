import {
  type Fields,
  list,
  oneOf,
  optionalOneOf,
  optionalText,
  PayloadFormatError,
  record,
  text,
  withOptional,
} from "@/shared/api/payload"
import { AVAILABILITIES, type OfferAttribute, type OfferView, SELLER_STATUSES } from "./model"
import { parseSource } from "./parse"

const DECIMAL = /^\d+(?:\.\d+)?$/
const WEB_ADDRESS = /^https?:\/\/\S+$/i

export function parsePrice(fields: Fields, path: string): number | undefined {
  const value = optionalText(fields, "price", path)
  if (value === undefined || value === "") return undefined
  if (!DECIMAL.test(value)) throw new PayloadFormatError(`${path}.price`)
  return Number(value)
}

function filled(fields: Fields, key: string, path: string): string | undefined {
  const value = optionalText(fields, key, path)?.trim()
  return value ? value : undefined
}

function attribute(value: unknown, path: string): OfferAttribute {
  const fields = record(value, path)
  return { name: text(fields, "name", path), value: text(fields, "value", path) }
}

function attributes(fields: Fields, path: string): OfferAttribute[] | undefined {
  if (fields.attributes === undefined || fields.attributes === null) return undefined
  const found = list(fields, "attributes", path, attribute).filter(
    (entry) => entry.name.trim() !== "" && entry.value.trim() !== "",
  )
  return found.length > 0 ? found : undefined
}

function imageUrl(fields: Fields, path: string): string | undefined {
  const value = filled(fields, "imageUrl", path)
  return value && WEB_ADDRESS.test(value) ? value : undefined
}

export function parseOffer(value: unknown, path: string): OfferView {
  const fields = record(value, path)
  return withOptional(
    {
      id: text(fields, "id", path),
      name: text(fields, "name", path),
      availability: oneOf(AVAILABILITIES, fields, "availability", path),
    },
    {
      price: parsePrice(fields, path),
      currency: filled(fields, "currency", path),
      unit: filled(fields, "unit", path),
      brand: filled(fields, "brand", path),
      article: filled(fields, "article", path),
      okpd2: filled(fields, "okpd2", path),
      attributes: attributes(fields, path),
      imageUrl: imageUrl(fields, path),
      seller: optionalOneOf(SELLER_STATUSES, fields, "seller", path),
      source: parseSource(fields.source, `${path}.source`),
    },
  )
}

export function parseOfferMap(value: unknown, path: string): Record<string, OfferView> {
  if (value === undefined || value === null) return {}
  const fields = record(value, path)
  return Object.fromEntries(
    Object.keys(fields).map((key) => {
      const offer = parseOffer(fields[key], `${path}.${key}`)
      if (offer.id !== key) throw new PayloadFormatError(`${path}.${key}.id`)
      return [key, offer]
    }),
  )
}
