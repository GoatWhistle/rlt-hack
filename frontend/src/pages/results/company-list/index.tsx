import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Stack } from "@/shared/ui/stack"
import { Tag } from "@/shared/ui/tag"
import { ResultSection } from "../section"
import { statusText } from "../status"
import styles from "./styles.module.css"

export function StatusTag({ company }: { readonly company: Company }) {
  const { t } = useTranslation()
  const recommended = company.status === "recommended"
  return (
    <Tag tone={recommended ? "solid" : "tentative"}>
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
  readonly totalProducts: number
  readonly selectedId: string
  readonly onSelect: (id: string) => void
}

export function CompanyList({
  companies,
  totalProducts,
  selectedId,
  onSelect,
}: CompanyListProps) {
  const { t } = useTranslation()
  return (
    <ResultSection title={t("results.companies.title")}>
      <Stack>
        {companies.map((company, index) => (
          <button
            key={company.id}
            type="button"
            aria-pressed={company.id === selectedId}
            className={clsx(styles.company, company.id === selectedId && styles.selected)}
            onClick={() => onSelect(company.id)}
          >
            <span className={styles.rank}>{index + 1}</span>
            <span className={styles.body}>
              <span className={styles.name}>{company.name}</span>
              <Caption>{company.role}</Caption>
              <span className={styles.facts}>
                <StatusTag company={company} />
                <span>
                  {t("results.companies.matchCount", {
                    matched: company.matches.length,
                    total: totalProducts,
                  })}
                </span>
                <span>
                  {t("results.companies.purchases", { count: company.similarPurchases })}
                </span>
              </span>
            </span>
          </button>
        ))}
      </Stack>
    </ResultSection>
  )
}
