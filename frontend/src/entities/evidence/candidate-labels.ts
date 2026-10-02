import { useTranslation } from "react-i18next"
import { useFormatters } from "@/shared/i18n/formatters"
import { useStatusLabel } from "./labels"
import type { CheckReason } from "./model"
import {
  type CandidateView,
  freshestOf,
  type ItemView,
  lastWinOf,
  matchFor,
  sortReasons,
} from "./view"

export function useReasonShort(): (reason: CheckReason) => string {
  const { t } = useTranslation("candidate")
  return (reason) => t(`reasonShort.${reason}`)
}

export function useCheckReasonText(): (reason: CheckReason) => string {
  const { t } = useTranslation("candidate")
  return (reason) =>
    t("reasonLine", { title: t(`reasonShort.${reason}`), value: t(`reasonText.${reason}`) })
}

export function useStatusText(): (candidate: CandidateView) => string {
  const { t } = useTranslation("candidate")
  const statusLabel = useStatusLabel()
  return (candidate) => {
    const [first, ...rest] = sortReasons(candidate.checkReasons)
    if (candidate.status !== "check" || !first) return statusLabel(candidate.status)
    const more = rest.length > 0 ? ` ${t("card.moreReasons", { count: rest.length })}` : ""
    return `${t(`reasonShort.${first}`)}${more}`
  }
}

export function useHistoryLine(): (candidate: CandidateView) => string | undefined {
  const { t } = useTranslation("candidate")
  return ({ similarPurchases, wins }) => {
    if (similarPurchases <= 0 && wins <= 0) return undefined
    const parts = [t("card.similar", { count: similarPurchases })]
    if (wins > 0) parts.push(t("card.wins", { count: wins }))
    return parts.join(" · ")
  }
}

function usePriceFact(): (candidate: CandidateView) => string | undefined {
  const { t } = useTranslation("candidate")
  const { t: evidence } = useTranslation("evidence")
  const { date } = useFormatters()
  return (candidate) => {
    const fresh = freshestOf(candidate)
    if (!fresh) return undefined
    if (fresh.checkedAt) {
      return t(fresh.basis === "stock" ? "summary.price" : "summary.catalog", {
        count: fresh.count,
        date: date(fresh.checkedAt),
      })
    }
    return fresh.basis === "stock"
      ? evidence("highlight.inStock", { count: fresh.count })
      : undefined
  }
}

function useWinFact(): (candidate: CandidateView) => string | undefined {
  const { t } = useTranslation("candidate")
  return (candidate) => {
    const win = lastWinOf(candidate)
    if (!win?.lotId) return undefined
    return win.year
      ? t("summary.winYear", { id: win.lotId, date: String(win.year) })
      : t("summary.win", { id: win.lotId })
  }
}

export function useSummaryText(): (candidate: CandidateView) => string {
  const { t } = useTranslation("candidate")
  const priceFact = usePriceFact()
  const winFact = useWinFact()
  return (candidate) => {
    const verified = candidate.highlights.some((item) => item.code === "verifiedIdentity")
    const parts = [
      priceFact(candidate),
      winFact(candidate),
      verified ? t("summary.verified") : undefined,
    ].filter((part): part is string => Boolean(part))
    if (parts.length === 0) return t("panel.noHighlights")
    const text = parts.join(t("summary.separator"))
    return `${text.charAt(0).toLocaleUpperCase()}${text.slice(1)}.`
  }
}

export function useClarifyItems(): (
  candidate: CandidateView,
  items: readonly ItemView[],
) => string[] {
  const { t } = useTranslation("candidate")
  return (candidate, items) => {
    const reasons = sortReasons(candidate.checkReasons).map((reason) =>
      t(`clarify.reason.${reason}`),
    )
    const confirm = items
      .filter((item) => {
        const match = matchFor(candidate, item.id)
        return match !== undefined && match.basis !== "stock"
      })
      .map((item) => t("clarify.item", { name: item.name }))
    return [...reasons, ...confirm]
  }
}
