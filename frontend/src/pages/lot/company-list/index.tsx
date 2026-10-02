import { clsx } from "clsx"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { FilterNote } from "@/shared/ui/filter-note"
import { Icon } from "@/shared/ui/icon"
import { PickCard } from "@/shared/ui/pick-card"
import { ResultSection } from "@/shared/ui/result-section"
import { Stack } from "@/shared/ui/stack"
import { Tag } from "@/shared/ui/tag"
import { TextButton } from "@/shared/ui/text-button"
import { SegmentMeter } from "../segment-meter"
import { useStatusText } from "../status"
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

function CompanyFacts({
  company,
  products,
}: {
  readonly company: Company
  readonly products: readonly Product[]
}) {
  const { t } = useTranslation("lot")
  return (
    <>
      {company.similarPurchases !== null && company.history ? (
        <span>
          {t("grounds.purchases", { count: company.similarPurchases })}
          {" · "}
          {t("grounds.winsCount", { count: company.wins ?? 0 })}
        </span>
      ) : company.history ? (
        <span>{t("history.examples", { count: company.history.examples.length })}</span>
      ) : (
        <span>
          {products.length === 0
            ? t("compare.unknown")
            : t("companies.matchCount", {
                matched: company.matches.length,
                total: products.length,
              })}
          {" · "}
          {company.similarPurchases === null
            ? t("compare.unknown")
            : t("companies.purchases", { count: company.similarPurchases })}
        </span>
      )}
    </>
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
            subtitle={company.role}
            rank={ranks.get(company.id) ?? 0}
            selected={company.id === selectedId}
            onSelect={() => onSelect(company.id)}
          >
            <SegmentMeter company={company} products={products} />
            <span className={styles.facts}>
              <StatusTag company={company} />
              {chosen.includes(company.id) ? (
                <Tag tone="accent">{t("companies.chosen")}</Tag>
              ) : null}
              <CompanyFacts company={company} products={products} />
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
