import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { MatchBasis } from "@/entities/evidence/model"
import { SegmentMeter } from "@/entities/evidence/ui/segment-meter"
import type { Company, Product } from "@/entities/recommendation/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import { Dialog } from "@/shared/ui/dialog"
import { ScrollRegion } from "@/shared/ui/scroll-region"
import { companySegments, useClarifyItems, useRoleText, useStatusText } from "../status"
import styles from "./styles.module.css"

export type CompareDialogProps = {
  readonly open: boolean
  readonly companies: readonly Company[]
  readonly products: readonly Product[]
  readonly onClose: () => void
}

type Criterion = {
  readonly id: string
  readonly label: string
  readonly value: (company: Company) => ReactNode
}

export function CompareDialog({ open, companies, products, onClose }: CompareDialogProps) {
  const { t } = useTranslation("lot")
  const { t: label } = useTranslation("evidence")
  const statusText = useStatusText()
  const roleText = useRoleText()
  const clarifyItems = useClarifyItems()
  const { list, number } = useFormatters()
  const count = (company: Company, basis: MatchBasis) =>
    number(company.matches.filter((match) => match.basis === basis).length)
  const unmatched = (company: Company) => {
    const found = new Set(company.matches.map((match) => match.productId))
    const names = products.filter((product) => !found.has(product.id)).map((p) => p.name)
    return names.length > 0 ? list(names) : t("compare.none")
  }
  const contacts = (company: Company) => {
    const { site, email, phone } = company.contacts ?? {}
    const known = [site, email, phone].filter(Boolean)
    return known.length > 0 ? known.join(" · ") : t("compare.unknown")
  }
  const criteria: Criterion[] = [
    {
      id: "match",
      label: t("compare.match"),
      value: (company) => (
        <span className={styles.match}>
          {t("companies.matchCount", {
            matched: company.matches.length,
            total: products.length,
          })}
          <SegmentMeter segments={companySegments(company, products)} />
        </span>
      ),
    },
    { id: "stock", label: label("basis.stock"), value: (c) => count(c, "stock") },
    { id: "catalog", label: label("basis.catalog"), value: (c) => count(c, "catalog") },
    { id: "inferred", label: label("basis.inferred"), value: (c) => count(c, "inferred") },
    { id: "missing", label: t("compare.missing"), value: unmatched },
    { id: "status", label: t("compare.status"), value: statusText },
    {
      id: "purchases",
      label: t("compare.purchases"),
      value: (c) => number(c.similarPurchases),
    },
    { id: "wins", label: t("compare.wins"), value: (c) => number(c.wins) },
    {
      id: "clarify",
      label: t("compare.clarify"),
      value: (c) => clarifyItems(c, products)[0] ?? t("compare.none"),
    },
    { id: "contacts", label: t("compare.contacts"), value: contacts },
    { id: "inn", label: t("profile.inn"), value: (c) => c.inn },
  ]
  return (
    <Dialog open={open} size="wide" title={t("compare.title")} onClose={onClose}>
      <ScrollRegion label={t("compare.title")} className={styles.region}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.criterion}>
                {t("compare.criterion")}
              </th>
              {companies.map((company) => (
                <th key={company.id} scope="col" className={styles.company}>
                  <span className={styles.companyName}>{company.name}</span>
                  <span className={styles.companyRole}>{roleText(company)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {criteria.map((criterion) => (
              <tr key={criterion.id}>
                <th scope="row" className={styles.criterion}>
                  {criterion.label}
                </th>
                {companies.map((company) => (
                  <td key={company.id} className={styles.cell}>
                    {criterion.value(company)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollRegion>
      <Caption>{t("compare.note")}</Caption>
    </Dialog>
  )
}
