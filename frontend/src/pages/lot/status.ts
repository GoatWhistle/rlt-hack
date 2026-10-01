import { useTranslation } from "react-i18next"
import { useHighlightText, useRoleLabel, useStatusLabel } from "@/entities/evidence/labels"
import type { MeterSegment } from "@/entities/evidence/ui/segment-meter"
import type { Company, Product } from "@/entities/recommendation/model"

export const SUMMARY_SEPARATOR = " · "

export function useStatusText(): (company: Company) => string {
  const { t } = useTranslation("lot")
  const statusLabel = useStatusLabel()
  return (company) => {
    const reason = company.checkReasons[0]
    if (company.status === "check" && reason) return t(`companies.checkReason.${reason}`)
    return statusLabel(company.status)
  }
}

export function useRoleText(): (company: Company) => string {
  const roleLabel = useRoleLabel()
  return (company) => roleLabel(company.role)
}

export function useSummaryText(): (company: Company) => string {
  const highlightText = useHighlightText()
  return (company) => company.highlights.map(highlightText).join(SUMMARY_SEPARATOR)
}

export function useClarifyItems(): (
  company: Company,
  products: readonly Product[],
) => string[] {
  const { t } = useTranslation("lot")
  return (company, products) => {
    const reasons = company.checkReasons.map((reason) => t(`clarify.reason.${reason}`))
    const unconfirmed = products.filter((product) =>
      company.matches.some(
        (match) => match.productId === product.id && match.basis !== "stock",
      ),
    )
    const confirm = unconfirmed.map((product) => t("clarify.product", { name: product.name }))
    return [...reasons, ...confirm]
  }
}

export function companySegments(
  company: Company,
  products: readonly Product[],
): MeterSegment[] {
  return products.map((product) => ({
    key: product.id,
    basis: company.matches.find((match) => match.productId === product.id)?.basis ?? "none",
  }))
}
