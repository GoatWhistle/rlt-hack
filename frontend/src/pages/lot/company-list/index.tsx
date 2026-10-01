import { clsx } from "clsx"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { Icon } from "@/shared/ui/icon"
import { Stack } from "@/shared/ui/stack"
import { Tag } from "@/shared/ui/tag"
import { TextButton } from "@/shared/ui/text-button"
import { ResultSection } from "../section"
import { SegmentMeter } from "../segment-meter"
import { useRoleText, useStatusText } from "../status"
import styles from "./styles.module.css"

export const VISIBLE_COMPANIES = 4

export function StatusTag({ company }: { readonly company: Company }) {
  const statusText = useStatusText()
  const recommended = company.status === "recommended"
  return (
    <Tag
      tone={company.status === "historical" ? "accent" : recommended ? "success" : "warning"}
    >
      <span
        aria-hidden="true"
        className={clsx(styles.dot, recommended ? styles.filled : styles.hollow)}
      />
      {statusText(company)}
    </Tag>
  )
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
        <p className={styles.filter}>
          <Icon name="filter" size="sm" />
          <span className={styles.filterText}>
            {t("companies.filtered", { name: filter.name })}
          </span>
          <TextButton onClick={filter.onReset}>{t("companies.resetFilter")}</TextButton>
        </p>
      ) : null}
      {companies.length === 0 ? <Caption>{t("companies.noMatch")}</Caption> : null}
      <Stack>
        {visible.map((company) => (
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
                <span className={styles.role}>{roleText(company)}</span>
              </span>
              <span className={styles.rank}>
                {String(ranks.get(company.id) ?? 0).padStart(2, "0")}
              </span>
            </span>
            <span className={styles.match}>
              <SegmentMeter company={company} products={products} />
              {products.length > 0 ? (
                <span className={styles.score} aria-hidden="true">
                  {number(company.matches.length)}/{number(products.length)}
                </span>
              ) : null}
            </span>
            <span className={styles.facts}>
              <span className={styles.tags}>
                <StatusTag company={company} />
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
          </button>
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
