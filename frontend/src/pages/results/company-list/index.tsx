import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company, CompanyStatus } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Stack } from "@/shared/ui/stack"
import { Tag } from "@/shared/ui/tag"
import { ResultSection } from "../section"
import styles from "./styles.module.css"

export function StatusTag({ status }: { readonly status: CompanyStatus }) {
  const { t } = useTranslation()
  return (
    <Tag>
      <span
        aria-hidden="true"
        className={clsx(styles.dot, status === "recommended" ? styles.filled : styles.hollow)}
      />
      {t(`results.companies.status.${status}`)}
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
    <ResultSection title={t("results.companies.title")} width="medium">
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
                <span className={styles.rank}>{index + 1}</span>
                <span>
                  <span className={styles.name}>{company.name}</span>
                  <Caption>
                    {t("results.companies.inn", { inn: company.inn })} · {company.role}
                  </Caption>
                </span>
              </span>
              <StatusTag status={company.status} />
            </span>
            <span className={styles.stats}>
              <span>
                {t("results.companies.covered", {
                  covered: company.coveredProductIds.length,
                  total: totalProducts,
                })}
              </span>
              <span>
                {t("results.companies.purchases", { count: company.similarPurchases })}
              </span>
            </span>
          </button>
        ))}
      </Stack>
    </ResultSection>
  )
}
