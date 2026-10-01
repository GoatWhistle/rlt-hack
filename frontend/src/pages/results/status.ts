import type { TFunction } from "i18next"
import type { Company } from "@/entities/recommendation/model"

export function statusText(company: Company, t: TFunction): string {
  if (company.status === "check" && company.checkReason) return company.checkReason
  return t(`results.companies.status.${company.status}`)
}
