import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { Stack } from "@/shared/ui/stack"
import { Tag } from "@/shared/ui/tag"
import { ResultSection } from "../section"
import { SegmentMeter } from "../segment-meter"
import { statusText } from "../status"
import styles from "./styles.module.css"

export function StatusTag({ company }: { readonly company: Company }) {
  const { t } = useTranslation()
  const recommended = company.status === "recommended"
  return (
    <Tag tone={recommended ? "success" : "warning"}>
      <span
        aria-hidden="true"
        className={clsx(styles.dot, recommended ? styles.filled : styles.hollow)}
      />
      {statusText(company, t)}
    </Tag>
  )
}

export type CompanyListProps = {
  readonly companies: readonly Company[]
  readonly products: readonly Product[]
  readonly selectedId: string
  readonly onSelect: (id: string) => void
}

export function CompanyList({ companies, products, selectedId, onSelect }: CompanyListProps) {
  const { t } = useTranslation()
  return (
    <ResultSection title={t("results.companies.title")} aside={t("results.companies.order")}>
      <Stack>
        {companies.map((company, index) => (
          <button
            key={company.id}
            type="button"
            aria-pressed={company.id === selectedId}
            className={clsx(styles.company, company.id === selectedId && styles.selected)}
            onClick={() => onSelect(company.id)}
          >
            <span className={styles.head}>
              <span className={styles.identity}>
                <span className={styles.name}>{company.name}</span>
                <span className={styles.role}>{company.role}</span>
              </span>
              <span className={styles.rank}>{String(index + 1).padStart(2, "0")}</span>
            </span>
            <SegmentMeter company={company} products={products} />
            <span className={styles.facts}>
              <StatusTag company={company} />
              <span>
                {t("results.companies.matchCount", {
                  matched: company.matches.length,
                  total: products.length,
                })}
                {" · "}
                {t("results.companies.purchases", { count: company.similarPurchases })}
              </span>
            </span>
          </button>
        ))}
      </Stack>
    </ResultSection>
  )
}
