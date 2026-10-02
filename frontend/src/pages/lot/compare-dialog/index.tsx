import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { Company, MatchBasis, Product } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Dialog } from "@/shared/ui/dialog"
import { ScrollRegion } from "@/shared/ui/scroll-region"
import { SegmentMeter } from "../segment-meter"
import { useStatusText } from "../status"
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
  const statusText = useStatusText()
  const count = (company: Company, basis: MatchBasis) =>
    company.matches.filter((match) => match.basis === basis).length
  const unmatched = (company: Company) => {
    const found = new Set(company.matches.map((match) => match.productId))
    const names = products.filter((product) => !found.has(product.id)).map((p) => p.name)
    return names.length > 0 ? names.join(", ") : t("compare.none")
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
          <SegmentMeter company={company} products={products} />
        </span>
      ),
    },
    { id: "stock", label: t("evidence.basis.stock"), value: (c) => count(c, "stock") },
    { id: "catalog", label: t("evidence.basis.catalog"), value: (c) => count(c, "catalog") },
    { id: "inferred", label: t("evidence.basis.inferred"), value: (c) => count(c, "inferred") },
    { id: "missing", label: t("compare.missing"), value: unmatched },
    { id: "status", label: t("compare.status"), value: statusText },
    {
      id: "purchases",
      label: t("compare.purchases"),
      value: (c) => c.similarPurchases ?? t("compare.unknown"),
    },
    { id: "wins", label: t("compare.wins"), value: (c) => c.wins ?? t("compare.unknown") },
    {
      id: "clarify",
      label: t("compare.clarify"),
      value: (c) => c.clarify[0] ?? t("compare.none"),
    },
    { id: "contacts", label: t("compare.contacts"), value: contacts },
    { id: "inn", label: t("profile.inn"), value: (c) => c.inn },
  ]
  return (
    <Dialog open={open} size="wide" title={t("compare.title")} onClose={onClose}>
      <ScrollRegion label={t("compare.title")}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.criterion}>
                {t("compare.criterion")}
              </th>
              {companies.map((company) => (
                <th key={company.id} scope="col" className={styles.company}>
                  {company.name}
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
