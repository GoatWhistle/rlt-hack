import { COMPANY_ROLES } from "@/entities/evidence/model"
import { parseContacts, parseSource } from "@/entities/evidence/parse"
import {
  type Fields,
  list,
  oneOf,
  optionalText,
  PayloadFormatError,
  plainText,
  record,
  text,
  withOptional,
} from "@/shared/api/payload"
import { AVAILABILITIES, IDENTITY_STATUSES, type Offer, type SupplierProfile } from "./model"

const DECIMAL = /^\d+(?:\.\d+)?$/

function price(fields: Fields, path: string): number | undefined {
  const value = optionalText(fields, "price", path)
  if (value === undefined || value === "") return undefined
  if (!DECIMAL.test(value)) throw new PayloadFormatError(`${path}.price`)
  return Number(value)
}

function offer(value: unknown, path: string): Offer {
  const fields = record(value, path)
  return withOptional(
    {
      id: text(fields, "id", path),
      name: text(fields, "name", path),
      currency: text(fields, "currency", path),
      unit: text(fields, "unit", path),
      availability: oneOf(AVAILABILITIES, fields, "availability", path),
    },
    { price: price(fields, path), source: parseSource(fields.source, `${path}.source`) },
  )
}

export function parseSupplierProfile(value: unknown): SupplierProfile {
  const fields = record(value, "$")
  return withOptional(
    {
      id: text(fields, "id", "$"),
      name: text(fields, "name", "$"),
      inn: text(fields, "inn", "$"),
      kpps: list(fields, "kpps", "$", plainText),
      region: text(fields, "region", "$"),
      identity: oneOf(IDENTITY_STATUSES, fields, "identity", "$"),
      role: oneOf(COMPANY_ROLES, fields, "role", "$"),
      contacts: parseContacts(record(fields.contacts, "$.contacts"), "$.contacts") ?? {},
      offers: list(fields, "offers", "$", offer),
    },
    { roleSource: parseSource(fields.roleSource, "$.roleSource") },
  )
}
