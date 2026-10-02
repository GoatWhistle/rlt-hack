import { clsx } from "clsx"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useMatchFigure } from "@/entities/evidence/labels"
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

const STATUS_TONES = {
  recommended: { tone: "accent", dot: styles.filled },
  check: { tone: "warning", dot: styles.hollow },
  historical: { tone: "solid", dot: styles.neutral },
} as const

export function StatusTag({ company }: { readonly company: Company }) {
  const statusText = useStatusText()
  const { tone, dot } = STATUS_TONES[company.status]
  return (
    <Tag tone={tone}>
      <span aria-hidden="true" className={clsx(styles.dot, dot)} />
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
  const { t: card } = useTranslation("candidate")
  const figureOf = useMatchFigure()
  if (company.history) {
    return company.similarPurchases !== null ? (
      <span>
        {t("grounds.purchases", { count: company.similarPurchases })}
        {" · "}
        {t("grounds.winsCount", { count: company.wins ?? 0 })}
      </span>
    ) : (
      <span>{t("history.examples", { count: company.history.examples.length })}</span>
    )
  }
  const figure = products.length > 0 ? figureOf(company.matches, products.length) : undefined
  const similar = company.similarPurchases ?? 0
  return (
    <>
      {figure ? (
        <span className={styles.figure}>
          {figure.value}
          {figure.note ? <span className={styles.assumed}> {figure.note}</span> : null}
        </span>
      ) : null}
      {similar > 0 ? (
        <span>
          {card("card.similar", { count: similar })}
          {company.wins ? ` · ${card("card.wins", { count: company.wins })}` : null}
        </span>
      ) : null}
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
  const { t: rankText } = useTranslation("candidate")
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
            rankLabel={rankText("card.rank", { index: ranks.get(company.id) ?? 0 })}
            selected={company.id === selectedId}
            onSelect={() => onSelect(company.id)}
          >
            <SegmentMeter company={company} products={products} />
            <span className={styles.facts}>
              <StatusTag company={company} />
              {chosen.includes(company.id) ? (
                <Tag tone="accent">
                  <Icon name="check" size="sm" />
                  {t("companies.chosen")}
                </Tag>
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
