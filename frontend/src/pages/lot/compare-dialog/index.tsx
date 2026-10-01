import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { useMatchFigure } from "@/entities/evidence/labels"
import { countMatches, type MatchBasis } from "@/entities/evidence/model"
import { SegmentMeter } from "@/entities/evidence/ui/segment-meter"
import type { Company, Product } from "@/entities/recommendation/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import { Dialog } from "@/shared/ui/dialog"
import { Icon } from "@/shared/ui/icon"
import { ScrollRegion } from "@/shared/ui/scroll-region"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import { CompanyStatus } from "../company-list"
import { companySegments, useClarifyItems, useRoleText } from "../status"
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
  readonly score?: (company: Company) => number
}

export function bestOf(
  companies: readonly Company[],
  score: ((company: Company) => number) | undefined,
): string | undefined {
  if (!score || companies.length < 2) return undefined
  const ranked = companies.map((company) => ({ id: company.id, value: score(company) }))
  const top = Math.max(...ranked.map((item) => item.value))
  const leaders = ranked.filter((item) => item.value === top)
  return leaders.length === 1 && top > 0 ? leaders[0]?.id : undefined
}

export function CompareDialog({ open, companies, products, onClose }: CompareDialogProps) {
  const { t } = useTranslation("lot")
  const { t: label } = useTranslation("evidence")
  const figureOf = useMatchFigure()
  const roleText = useRoleText()
  const clarifyItems = useClarifyItems()
  const { list, number } = useFormatters()
  const amount = (company: Company, basis: MatchBasis) =>
    company.matches.filter((match) => match.basis === basis).length
  const count = (company: Company, basis: MatchBasis) => number(amount(company, basis))
  const unmatched = (company: Company) => {
    const found = new Set(company.matches.map((match) => match.productId))
    const names = products.filter((product) => !found.has(product.id)).map((p) => p.name)
    if (names.length === 0) return t("compare.none")
    return (
      <span className={styles.missing}>
        <span className={styles.marker} aria-hidden="true" />
        {list(names)}
      </span>
    )
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
      value: (company) => {
        const figure = figureOf(company.matches, products.length)
        return (
          <span className={styles.match}>
            <span>
              {figure.value}
              {figure.note ? <span className={styles.note}> {figure.note}</span> : null}
            </span>
            <SegmentMeter segments={companySegments(company, products)} />
          </span>
        )
      },
      score: (c) => countMatches(c.matches).confirmed,
    },
    {
      id: "stock",
      label: label("basis.stock"),
      value: (c) => count(c, "stock"),
      score: (c) => amount(c, "stock"),
    },
    {
      id: "catalog",
      label: label("basis.catalog"),
      value: (c) => count(c, "catalog"),
      score: (c) => amount(c, "catalog"),
    },
    { id: "inferred", label: label("basis.inferred"), value: (c) => count(c, "inferred") },
    { id: "missing", label: t("compare.missing"), value: unmatched },
    {
      id: "status",
      label: t("compare.status"),
      value: (c) => <CompanyStatus company={c} />,
    },
    {
      id: "purchases",
      label: t("compare.purchases"),
      value: (c) => number(c.similarPurchases),
      score: (c) => c.similarPurchases,
    },
    {
      id: "wins",
      label: t("compare.wins"),
      value: (c) => number(c.wins),
      score: (c) => c.wins,
    },
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
            {criteria.map((criterion) => {
              const best = bestOf(companies, criterion.score)
              return (
                <tr key={criterion.id}>
                  <th scope="row" className={styles.criterion}>
                    {criterion.label}
                  </th>
                  {companies.map((company) => (
                    <td key={company.id} className={styles.cell}>
                      {company.id === best ? (
                        <span className={styles.best}>
                          <Icon name="check" size="sm" />
                          {criterion.value(company)}{" "}
                          <VisuallyHidden>{t("compare.best")}</VisuallyHidden>
                        </span>
                      ) : (
                        criterion.value(company)
                      )}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </ScrollRegion>
      <Caption>{t("compare.note")}</Caption>
    </Dialog>
  )
}
