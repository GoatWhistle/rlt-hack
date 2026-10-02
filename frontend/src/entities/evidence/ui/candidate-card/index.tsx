import type { KeyboardEvent } from "react"
import { useTranslation } from "react-i18next"
import { useStatusText } from "@/entities/evidence/candidate-labels"
import { useInnText, useRoleLabel } from "@/entities/evidence/labels"
import { countMatches } from "@/entities/evidence/model"
import { useOfferText } from "@/entities/evidence/offer-labels"
import type { CandidateView, ItemView, MatchView } from "@/entities/evidence/view"
import { segmentsOf } from "@/entities/evidence/view"
import { useFormatters } from "@/shared/i18n/formatters"
import { FactRow } from "@/shared/ui/fact-row"
import { Icon } from "@/shared/ui/icon"
import { PickCard } from "@/shared/ui/pick-card"
import { Tag } from "@/shared/ui/tag"
import { HistoryChips } from "../history-chips"
import { BasisMarker } from "../match-row"
import { SegmentMeter } from "../segment-meter"
import { StatusTag } from "../status-tag"
import styles from "./styles.module.css"

export type CandidateCardProps = {
  readonly candidate: CandidateView
  readonly items: readonly ItemView[]
  readonly selected: boolean
  readonly chosen: boolean
  readonly focus?: MatchView
  readonly reveal?: number
  readonly tabIndex?: number
  readonly onSelect: () => void
  readonly onKeyDown?: (event: KeyboardEvent<HTMLButtonElement>) => void
}

export function CandidateCard({
  candidate,
  items,
  selected,
  chosen,
  focus,
  reveal,
  tabIndex,
  onSelect,
  onKeyDown,
}: CandidateCardProps) {
  const { t } = useTranslation("candidate")
  const roleLabel = useRoleLabel()
  const innText = useInnText()
  const statusText = useStatusText()
  const history = candidate.similarPurchases > 0 || candidate.wins > 0
  return (
    <PickCard
      title={candidate.name}
      subtitle={
        <FactRow>
          <span>{roleLabel(candidate.role)}</span>
          <span className={candidate.inn ? styles.inn : undefined}>
            {innText(candidate.inn)}
          </span>
        </FactRow>
      }
      rank={candidate.rank}
      rankLabel={t("card.rank", { index: candidate.rank })}
      selected={selected}
      reveal={reveal}
      tabIndex={tabIndex}
      onSelect={onSelect}
      onKeyDown={onKeyDown}
    >
      {focus ? <FocusLine match={focus} /> : null}
      <span className={styles.match}>
        <SegmentMeter segments={segmentsOf(candidate, items)} reveal={reveal !== undefined} />
        <MatchScore candidate={candidate} total={items.length} />
      </span>
      <span className={styles.facts}>
        <span className={styles.tags}>
          <StatusTag status={candidate.status}>{statusText(candidate)}</StatusTag>
          {chosen ? (
            <span className={styles.chosen}>
              <Tag tone="accent">
                <Icon name="check" size="sm" />
                {t("card.chosen")}
              </Tag>
            </span>
          ) : null}
        </span>
        {history ? (
          <span className={styles.history}>
            <HistoryChips similar={candidate.similarPurchases} wins={candidate.wins} />
          </span>
        ) : null}
      </span>
    </PickCard>
  )
}

function FocusLine({ match }: { readonly match: MatchView }) {
  const { t: evidence } = useTranslation("evidence")
  const { date } = useFormatters()
  const offerText = useOfferText()
  const checkedAt = match.source?.checkedAt
  const offer =
    match.offer?.price !== undefined && match.basis !== "inferred" ? match.offer : undefined
  return (
    <span className={styles.focus} data-basis={match.basis}>
      <BasisMarker basis={match.basis} />
      <span className={styles.focusText}>
        <FactRow>
          {offer ? (
            <span className={styles.price}>{offerText.price(offer)}</span>
          ) : (
            <span>{evidence(`basis.${match.basis}`)}</span>
          )}
          {offer ? (
            <span>{offerText.availability(offer.availability ?? "unknown")}</span>
          ) : null}
          {checkedAt ? <span className={styles.date}>{date(checkedAt)}</span> : null}
        </FactRow>
      </span>
    </span>
  )
}

function MatchScore({
  candidate,
  total,
}: {
  readonly candidate: CandidateView
  readonly total: number
}) {
  const { number } = useFormatters()
  const { confirmed, assumed } = countMatches(candidate.matches)
  return (
    <span className={styles.score} aria-hidden="true">
      {number(confirmed)}/{number(total)}
      {assumed > 0 ? <span className={styles.assumed}>+{number(assumed)}</span> : null}
    </span>
  )
}
