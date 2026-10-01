import { useTranslation } from "react-i18next"
import type { Company } from "@/entities/recommendation/model"

export function useStatusText(): (company: Company) => string {
  const { t } = useTranslation("lot")
  return (company) => {
    if (company.status === "check" && company.checkReason) return company.checkReason
    return t(`companies.status.${company.status}`)
  }
}
