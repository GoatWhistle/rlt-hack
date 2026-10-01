import { useState } from "react"
import { useTranslation } from "react-i18next"
import { SegmentMeter } from "@/entities/evidence/ui/segment-meter"
import { StatusTag } from "@/entities/evidence/ui/status-tag"
import type { Company, Product } from "@/entities/recommendation/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { FilterNote } from "@/shared/ui/filter-note"
import { Icon } from "@/shared/ui/icon"
import { PickCard } from "@/shared/ui/pick-card"
import { ResultSection } from "@/shared/ui/result-section"
import { Stack } from "@/shared/ui/stack"
import { Tag } from "@/shared/ui/tag"
import { TextButton } from "@/shared/ui/text-button"
import { companySegments, useRoleText, useStatusText } from "../status"
import styles from "./styles.module.css"

export const VISIBLE_COMPANIES = 4

export function CompanyStatus({ company }: { readonly company: Company }) {
  const statusText = useStatusText()
  return <StatusTag status={company.status}>{statusText(company)}</StatusTag>
}

export type CompanyListProps = {
  readonly companies: readonly Company[]
  readonly ranks: ReadonlyMap<string, number>
  readonly products: readonly Product[]
  readonly selectedId: string
  readonly chosen: readonly string[]
  readonly filter?: { readonly name: string; readonly onReset: () => void }
  readonly onSelect: (id: string) => void
  readonly onCompare: () => void
}

export function CompanyList(props: CompanyListProps) {
  const { companies, ranks, products, selectedId, chosen, filter, onSelect, onCompare } = props
  const { t } = useTranslation("lot")
  const roleText = useRoleText()
  const { number } = useFormatters()
  const [expanded, setExpanded] = useState(false)
  const hidden = companies.length - VISIBLE_COMPANIES
  const visible = expanded || hidden <= 0 ? companies : companies.slice(0, VISIBLE_COMPANIES)
  return (
    <ResultSection title={t("companies.title")} aside={t("companies.order")}>
      {filter ? (
        <FilterNote
          text={t("companies.filtered", { name: filter.name })}
          resetLabel={t("companies.resetFilter")}
          onReset={filter.onReset}
        />
      ) : null}
      {companies.length === 0 ? <Caption>{t("companies.noMatch")}</Caption> : null}
      <Stack>
        {visible.map((company) => (
          <PickCard
            key={company.id}
            title={company.name}
            subtitle={roleText(company)}
            rank={ranks.get(company.id) ?? 0}
            selected={company.id === selectedId}
            onSelect={() => onSelect(company.id)}
          >
            <span className={styles.match}>
              <SegmentMeter segments={companySegments(company, products)} />
              <span className={styles.score} aria-hidden="true">
                {number(company.matches.length)}/{number(products.length)}
              </span>
            </span>
            <span className={styles.facts}>
              <span className={styles.tags}>
                <CompanyStatus company={company} />
                {chosen.includes(company.id) ? (
                  <Tag tone="accent">
                    <Icon name="check" size="sm" />
                    {t("companies.chosen")}
                  </Tag>
                ) : null}
              </span>
              <span className={styles.history}>
                {company.similarPurchases === null
                  ? t("compare.unknown")
                  : t("companies.purchases", { count: company.similarPurchases })}
              </span>
            </span>
          </PickCard>
        ))}
      </Stack>
      {hidden > 0 ? (
        <TextButton aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
          {expanded ? t("companies.showLess") : t("companies.showMore", { count: hidden })}
        </TextButton>
      ) : null}
      <div className={styles.compare}>
        {chosen.length >= 2 ? (
          <Button variant="secondary" onClick={onCompare}>
            <Icon name="compare" />
            {t("companies.compare", { count: chosen.length })}
          </Button>
        ) : (
          <Caption>{t("companies.compareHint")}</Caption>
        )}
      </div>
    </ResultSection>
  )
}
