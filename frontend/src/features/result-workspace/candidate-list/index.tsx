import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  useCompanyName,
  useHighlightText,
  useInnText,
  useRoleLabel,
  useStatusLabel,
} from "@/entities/evidence/labels"
import { NoveltyTag } from "@/entities/evidence/ui/novelty-tag"
import { StatusTag } from "@/entities/evidence/ui/status-tag"
import type { Candidate } from "@/entities/search/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import { FilterNote } from "@/shared/ui/filter-note"
import { Icon } from "@/shared/ui/icon"
import { PickCard } from "@/shared/ui/pick-card"
import { ResultSection } from "@/shared/ui/result-section"
import { ScoreBar } from "@/shared/ui/score-bar"
import { Stack } from "@/shared/ui/stack"
import { Tag } from "@/shared/ui/tag"
import { TextButton } from "@/shared/ui/text-button"
import styles from "./styles.module.css"

export const VISIBLE_CANDIDATES = 5
export const CARD_HIGHLIGHTS = 2

export type CandidateListProps = {
  readonly candidates: readonly Candidate[]
  readonly selectedId: string
  readonly chosen: readonly string[]
  readonly filter?: { readonly name: string; readonly onReset: () => void }
  readonly onSelect: (id: string) => void
}

function CandidateCard({
  candidate,
  selected,
  chosen,
  onSelect,
}: {
  readonly candidate: Candidate
  readonly selected: boolean
  readonly chosen: boolean
  readonly onSelect: () => void
}) {
  const { t } = useTranslation("search")
  const { number } = useFormatters()
  const roleLabel = useRoleLabel()
  const statusLabel = useStatusLabel()
  const highlightText = useHighlightText()
  const innText = useInnText()
  const nameOf = useCompanyName()
  const highlights = candidate.highlights.slice(0, CARD_HIGHLIGHTS).map(highlightText)
  return (
    <PickCard
      title={nameOf(candidate)}
      subtitle={
        <>
          {roleLabel(candidate.role)}
          {" · "}
          {candidate.inn ? (
            <span className={styles.inn}>{innText(candidate.inn)}</span>
          ) : (
            innText(candidate.inn)
          )}
        </>
      }
      rank={candidate.rank}
      selected={selected}
      onSelect={onSelect}
    >
      <ScoreBar
        showLabel
        value={candidate.score.total}
        label={t("candidates.score")}
        valueText={t("candidates.scoreValue", { value: number(candidate.score.total) })}
      />
      <span className={styles.facts}>
        <span className={styles.tags}>
          <StatusTag status={candidate.status}>{statusLabel(candidate.status)}</StatusTag>
          <NoveltyTag novelty={candidate.novelty} />
          {chosen ? (
            <Tag tone="accent">
              <Icon name="check" size="sm" />
              {t("candidates.chosen")}
            </Tag>
          ) : null}
        </span>
        {highlights.length > 0 ? (
          <span className={styles.highlights}>{highlights.join(" · ")}</span>
        ) : null}
      </span>
    </PickCard>
  )
}

export function CandidateList({
  candidates,
  selectedId,
  chosen,
  filter,
  onSelect,
}: CandidateListProps) {
  const { t } = useTranslation("search")
  const [expanded, setExpanded] = useState(false)
  const hidden = candidates.length - VISIBLE_CANDIDATES
  const visible = expanded || hidden <= 0 ? candidates : candidates.slice(0, VISIBLE_CANDIDATES)
  return (
    <ResultSection title={t("candidates.title")} aside={t("candidates.order")}>
      {filter ? (
        <FilterNote
          text={t("candidates.filtered", { name: filter.name })}
          resetLabel={t("candidates.resetFilter")}
          onReset={filter.onReset}
        />
      ) : null}
      {candidates.length === 0 ? <Caption>{t("candidates.noMatch")}</Caption> : null}
      <Stack>
        {visible.map((candidate) => (
          <CandidateCard
            key={candidate.id}
            candidate={candidate}
            selected={candidate.id === selectedId}
            chosen={chosen.includes(candidate.id)}
            onSelect={() => onSelect(candidate.id)}
          />
        ))}
      </Stack>
      {hidden > 0 ? (
        <TextButton aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
          {expanded ? t("candidates.showLess") : t("candidates.showMore", { count: hidden })}
        </TextButton>
      ) : null}
    </ResultSection>
  )
}
