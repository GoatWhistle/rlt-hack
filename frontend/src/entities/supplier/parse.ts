import { COMPANY_ROLES } from "@/entities/evidence/model"
import { parseOffer } from "@/entities/evidence/offer-parse"
import { parseContacts, parseSource } from "@/entities/evidence/parse"
import { list, oneOf, plainText, record, text, withOptional } from "@/shared/api/payload"
import { IDENTITY_STATUSES, type SupplierProfile } from "./model"

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
      offers: list(fields, "offers", "$", parseOffer),
    },
    { roleSource: parseSource(fields.roleSource, "$.roleSource") },
  )
}
