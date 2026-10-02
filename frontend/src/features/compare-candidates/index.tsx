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
import {
  type CompareColumn,
  type CompareCriterion,
  CompareTable,
  MatchValue,
  MissingNames,
} from "./compare-table"
import { useOfferCriteria } from "./offer-criteria"

export {
  bestOf,
  type CompareColumn,
  type CompareCriterion,
  CompareTable,
  MatchValue,
  MissingNames,
} from "./compare-table"

export type CompareDialogProps = {
  readonly open: boolean
  readonly candidates: readonly CandidateView[]
  readonly items: readonly ItemView[]
  readonly onClose: () => void
}

type Column = CompareColumn & { readonly candidate: CandidateView }

function useCriteria(
  items: readonly ItemView[],
  candidates: readonly CandidateView[],
): CompareCriterion<Column>[] {
  const { t } = useTranslation("candidate")
  const { t: label } = useTranslation("evidence")
  const figureOf = useMatchFigure()
  const statusText = useStatusText()
  const clarifyItems = useClarifyItems()
  const { list, number } = useFormatters()
  const offers = useOfferCriteria<Column>(items, candidates)
  const amount = (candidate: CandidateView, basis: MatchBasis) =>
    candidate.matches.filter((match) => match.basis === basis).length
  const unmatched = (candidate: CandidateView) => {
    const names = items.filter((item) => !matchFor(candidate, item.id)).map((item) => item.name)
    return names.length === 0 ? t("compare.none") : <MissingNames names={list(names)} />
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
      value: ({ candidate }) => {
        const figure = figureOf(candidate.matches, items.length)
        return (
          <MatchValue
            figure={figure.value}
            note={figure.note}
            meter={<SegmentMeter segments={segmentsOf(candidate, items)} />}
          />
        )
      },
      score: ({ candidate }) => countMatches(candidate.matches).confirmed,
    },
    ...offers,
    {
      id: "stock",
      label: label("basis.stock"),
      value: ({ candidate }) => number(amount(candidate, "stock")),
      score: ({ candidate }) => amount(candidate, "stock"),
    },
    {
      id: "catalog",
      label: label("basis.catalog"),
      value: ({ candidate }) => number(amount(candidate, "catalog")),
    },
    {
      id: "inferred",
      label: label("basis.inferred"),
      value: ({ candidate }) => number(amount(candidate, "inferred")),
    },
    {
      id: "missing",
      label: t("compare.missing"),
      value: ({ candidate }) => unmatched(candidate),
    },
    {
      id: "status",
      label: t("compare.status"),
      value: ({ candidate }) => (
        <StatusTag status={candidate.status}>{statusText(candidate)}</StatusTag>
      ),
    },
    {
      id: "purchases",
      label: t("compare.purchases"),
      value: ({ candidate }) => number(candidate.similarPurchases),
      score: ({ candidate }) => candidate.similarPurchases,
    },
    {
      id: "wins",
      label: t("compare.wins"),
      value: ({ candidate }) => number(candidate.wins),
      score: ({ candidate }) => candidate.wins,
    },
    {
      id: "clarify",
      label: t("compare.clarify"),
      value: ({ candidate }) => clarifyItems(candidate, items)[0] ?? t("compare.none"),
    },
    {
      id: "contacts",
      label: t("compare.contacts"),
      value: ({ candidate }) => contacts(candidate),
    },
    {
      id: "inn",
      label: t("panel.inn"),
      value: ({ candidate }) => candidate.inn || t("compare.unknown"),
    },
  ]
}

export function CompareDialog({ open, candidates, items, onClose }: CompareDialogProps) {
  const { t } = useTranslation("candidate")
  const roleLabel = useRoleLabel()
  const criteria = useCriteria(items, candidates)
  return (
    <CompareTable
      open={open}
      title={t("compare.title")}
      criterionLabel={t("compare.criterion")}
      bestLabel={t("compare.best")}
      note={t("compare.note")}
      columns={candidates.map((candidate) => ({
        id: candidate.id,
        name: candidate.name,
        role: roleLabel(candidate.role),
        candidate,
      }))}
      criteria={criteria}
      onClose={onClose}
    />
  )
}
