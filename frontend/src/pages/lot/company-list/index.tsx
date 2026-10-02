import { clsx } from "clsx"
import { type KeyboardEvent, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useInnText, useMatchFigure } from "@/entities/evidence/labels"
import { targetIndex, useRevealSelected } from "@/entities/evidence/ui/candidate-list"
import { HistoryChips } from "@/entities/evidence/ui/history-chips"
import type { Company, Product } from "@/entities/recommendation/model"
import { COMPARE_FROM } from "@/features/compare-candidates"
import { Caption } from "@/shared/ui/caption"
import { FactRow } from "@/shared/ui/fact-row"
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
    <Tag tone={tone} wrap>
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
  const figureOf = useMatchFigure()
  if (company.history) {
    return company.similarPurchases !== null ? (
      <HistoryChips similar={company.similarPurchases} wins={company.wins ?? 0} />
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
      {similar > 0 ? <HistoryChips similar={similar} wins={company.wins ?? 0} /> : null}
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
}

export function CompanyList(props: CompanyListProps) {
  const { companies, ranks, products, selectedId, chosen, filter, onSelect } = props
  const { t } = useTranslation("lot")
  const { t: rankText } = useTranslation("candidate")
  const innText = useInnText()
  const [expanded, setExpanded] = useState(
    () => companies.findIndex((company) => company.id === selectedId) >= VISIBLE_COMPANIES,
  )
  const hidden = companies.length - VISIBLE_COMPANIES
  const visible = expanded || hidden <= 0 ? companies : companies.slice(0, VISIBLE_COMPANIES)
  const listRef = useRef<HTMLDivElement>(null)
  const selectedVisible = visible.some((company) => company.id === selectedId)
  useRevealSelected(listRef)

  function move(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.altKey || event.ctrlKey || event.metaKey) return
    const next = targetIndex(event.key, index, visible.length - 1)
    const target = next === null ? undefined : visible[next]
    if (!target || next === null) return
    event.preventDefault()
    onSelect(target.id)
    listRef.current?.querySelectorAll<HTMLButtonElement>("[aria-pressed]")[next]?.focus()
  }

  return (
    <ResultSection title={t("companies.title")}>
      {filter ? (
        <FilterNote
          text={t("companies.filtered", { name: filter.name })}
          resetLabel={t("companies.resetFilter")}
          onReset={filter.onReset}
        />
      ) : null}
      {companies.length === 0 ? <Caption>{t("companies.noMatch")}</Caption> : null}
      <div ref={listRef}>
        <Stack>
          {visible.map((company, index) => (
            <PickCard
              key={company.id}
              title={company.name}
              subtitle={
                <FactRow>
                  <span>{company.role}</span>
                  <span className={company.inn ? styles.inn : undefined}>
                    {innText(company.inn)}
                  </span>
                </FactRow>
              }
              rank={ranks.get(company.id) ?? 0}
              rankLabel={rankText("card.rank", { index: ranks.get(company.id) ?? 0 })}
              selected={company.id === selectedId}
              tabIndex={company.id === selectedId || (!selectedVisible && index === 0) ? 0 : -1}
              onSelect={() => onSelect(company.id)}
              onKeyDown={(event) => move(event, index)}
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
      </div>
      {hidden > 0 ? (
        <TextButton aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
          {expanded ? t("companies.showLess") : t("companies.showMore", { count: hidden })}
        </TextButton>
      ) : null}
      {chosen.length < COMPARE_FROM ? (
        <div className={styles.compare}>
          <Caption>{t("companies.compareHint")}</Caption>
        </div>
      ) : null}
    </ResultSection>
  )
}
