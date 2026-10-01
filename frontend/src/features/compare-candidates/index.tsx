import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { useClarifyItems, useStatusText } from "@/entities/evidence/candidate-labels"
import { useMatchFigure, useRoleLabel } from "@/entities/evidence/labels"
import { countMatches, type MatchBasis } from "@/entities/evidence/model"
import { SegmentMeter } from "@/entities/evidence/ui/segment-meter"
import { StatusTag } from "@/entities/evidence/ui/status-tag"
import {
  type CandidateView,
  type ItemView,
  matchFor,
  segmentsOf,
} from "@/entities/evidence/view"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import { Dialog } from "@/shared/ui/dialog"
import { Icon } from "@/shared/ui/icon"
import { ScrollRegion } from "@/shared/ui/scroll-region"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export type CompareDialogProps = {
  readonly open: boolean
  readonly candidates: readonly CandidateView[]
  readonly items: readonly ItemView[]
  readonly onClose: () => void
}

type Criterion = {
  readonly id: string
  readonly label: string
  readonly value: (candidate: CandidateView) => ReactNode
  readonly score?: (candidate: CandidateView) => number
}

export function bestOf(
  candidates: readonly CandidateView[],
  score: ((candidate: CandidateView) => number) | undefined,
): string | undefined {
  if (!score || candidates.length < 2) return undefined
  const ranked = candidates.map((candidate) => ({ id: candidate.id, value: score(candidate) }))
  const top = Math.max(...ranked.map((item) => item.value))
  const leaders = ranked.filter((item) => item.value === top)
  return leaders.length === 1 && top > 0 ? leaders[0]?.id : undefined
}

function useCriteria(items: readonly ItemView[]): Criterion[] {
  const { t } = useTranslation("candidate")
  const { t: label } = useTranslation("evidence")
  const figureOf = useMatchFigure()
  const statusText = useStatusText()
  const clarifyItems = useClarifyItems()
  const { list, number } = useFormatters()
  const amount = (candidate: CandidateView, basis: MatchBasis) =>
    candidate.matches.filter((match) => match.basis === basis).length
  const unmatched = (candidate: CandidateView) => {
    const names = items.filter((item) => !matchFor(candidate, item.id)).map((item) => item.name)
    if (names.length === 0) return t("compare.none")
    return (
      <span className={styles.missing}>
        <span className={styles.marker} aria-hidden="true" />
        {list(names)}
      </span>
    )
  }
  const contacts = (candidate: CandidateView) => {
    const { site, email, phone } = candidate.contacts ?? {}
    const known = [site, email, phone].filter(Boolean)
    return known.length > 0 ? known.join(" · ") : t("compare.unknown")
  }
  return [
    {
      id: "match",
      label: t("compare.match"),
      value: (candidate) => {
        const figure = figureOf(candidate.matches, items.length)
        return (
          <span className={styles.match}>
            <span>
              {figure.value}
              {figure.note ? <span className={styles.note}> {figure.note}</span> : null}
            </span>
            <SegmentMeter segments={segmentsOf(candidate, items)} />
          </span>
        )
      },
      score: (candidate) => countMatches(candidate.matches).confirmed,
    },
    {
      id: "stock",
      label: label("basis.stock"),
      value: (candidate) => number(amount(candidate, "stock")),
      score: (candidate) => amount(candidate, "stock"),
    },
    {
      id: "catalog",
      label: label("basis.catalog"),
      value: (candidate) => number(amount(candidate, "catalog")),
    },
    {
      id: "inferred",
      label: label("basis.inferred"),
      value: (candidate) => number(amount(candidate, "inferred")),
    },
    { id: "missing", label: t("compare.missing"), value: unmatched },
    {
      id: "status",
      label: t("compare.status"),
      value: (candidate) => (
        <StatusTag status={candidate.status}>{statusText(candidate)}</StatusTag>
      ),
    },
    {
      id: "purchases",
      label: t("compare.purchases"),
      value: (candidate) => number(candidate.similarPurchases),
      score: (candidate) => candidate.similarPurchases,
    },
    {
      id: "wins",
      label: t("compare.wins"),
      value: (candidate) => number(candidate.wins),
      score: (candidate) => candidate.wins,
    },
    {
      id: "clarify",
      label: t("compare.clarify"),
      value: (candidate) => clarifyItems(candidate, items)[0] ?? t("compare.none"),
    },
    { id: "contacts", label: t("compare.contacts"), value: contacts },
    {
      id: "inn",
      label: t("panel.inn"),
      value: (candidate) => candidate.inn || t("compare.unknown"),
    },
  ]
}

export function CompareDialog({ open, candidates, items, onClose }: CompareDialogProps) {
  const { t } = useTranslation("candidate")
  const roleLabel = useRoleLabel()
  const criteria = useCriteria(items)
  return (
    <Dialog open={open} size="wide" title={t("compare.title")} onClose={onClose}>
      <ScrollRegion label={t("compare.title")} className={styles.region}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.criterion}>
                {t("compare.criterion")}
              </th>
              {candidates.map((candidate) => (
                <th key={candidate.id} scope="col" className={styles.company}>
                  <span className={styles.companyName}>{candidate.name}</span>
                  <span className={styles.companyRole}>{roleLabel(candidate.role)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {criteria.map((criterion) => {
              const best = bestOf(candidates, criterion.score)
              return (
                <tr key={criterion.id}>
                  <th scope="row" className={styles.criterion}>
                    {criterion.label}
                  </th>
                  {candidates.map((candidate) => (
                    <td key={candidate.id} className={styles.cell}>
                      <span className={styles.value}>
                        <span className={styles.best}>
                          {candidate.id === best ? (
                            <>
                              <Icon name="check" size="sm" />
                              <VisuallyHidden>{t("compare.best")}</VisuallyHidden>
                            </>
                          ) : null}
                        </span>
                        <span className={candidate.id === best ? styles.leader : undefined}>
                          {criterion.value(candidate)}
                        </span>
                      </span>
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </ScrollRegion>
      <Caption>{t("compare.note")}</Caption>
    </Dialog>
  )
}
