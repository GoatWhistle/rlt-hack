import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import {
  useClarifyItems,
  useReasonShort,
  useSummaryText,
} from "@/entities/evidence/candidate-labels"
import {
  useInnText,
  useMatchFigure,
  useRoleLabel,
  useStatusLabel,
} from "@/entities/evidence/labels"
import {
  type CandidateView,
  type ItemView,
  segmentsOf,
  sortReasons,
} from "@/entities/evidence/view"
import { Icon } from "@/shared/ui/icon"
import { CandidateHero, type HeroReason } from "../candidate-hero"
import { CandidatePager, type CandidatePagerProps } from "../candidate-pager"
import { ClarifyBlock } from "../clarify-block"
import { CompanyBlock } from "../company-block"
import { EvidenceAction, EvidenceFrame } from "../evidence-frame"
import { SegmentMeter } from "../segment-meter"
import { StatusTag } from "../status-tag"
import { HistoryBlock, MatchBlock } from "./blocks"

export { offerEntries } from "./blocks"

export type CandidatePanelProps = {
  readonly candidate: CandidateView
  readonly items: readonly ItemView[]
  readonly chosen: boolean
  readonly pager?: CandidatePagerProps
  readonly focusItemId?: string
  readonly extraAction?: ReactNode
  readonly onChoose: () => void
  readonly onProfile: () => void
}

function useReason(): (candidate: CandidateView) => HeroReason {
  const { t } = useTranslation("candidate")
  const shortOf = useReasonShort()
  const summaryOf = useSummaryText()
  return (candidate) => {
    if (candidate.status !== "check") {
      return { title: t("panel.summaryTitle"), text: summaryOf(candidate) }
    }
    const points = sortReasons(candidate.checkReasons).map((reason) => ({
      key: reason,
      label: shortOf(reason),
      text: t(`reasonText.${reason}`),
    }))
    return { title: t("panel.checkTitle"), text: t("panel.noHighlights"), points }
  }
}

export function CandidatePanel({
  candidate,
  items,
  chosen,
  pager,
  focusItemId,
  extraAction,
  onChoose,
  onProfile,
}: CandidatePanelProps) {
  const { t } = useTranslation("candidate")
  const roleLabel = useRoleLabel()
  const statusLabel = useStatusLabel()
  const innText = useInnText()
  const figureOf = useMatchFigure()
  const reasonOf = useReason()
  const clarifyOf = useClarifyItems()
  return (
    <EvidenceFrame
      label={candidate.name}
      swapKey={candidate.id}
      extra={extraAction}
      actions={
        <>
          <EvidenceAction
            variant={chosen ? "secondary" : "primary"}
            icon={chosen ? <Icon name="check" /> : null}
            label={chosen ? t("panel.chosen") : t("panel.choose")}
            onClick={onChoose}
          />
          <EvidenceAction
            variant="secondary"
            label={t("panel.profile")}
            shortLabel={t("panel.profileShort")}
            onClick={onProfile}
          />
        </>
      }
    >
      <CandidateHero
        name={candidate.name}
        role={roleLabel(candidate.role)}
        code={innText(candidate.inn)}
        check={candidate.status === "check"}
        figure={{ ...figureOf(candidate.matches, items.length), label: t("panel.figure") }}
        verdict={
          <>
            <StatusTag status={candidate.status}>{statusLabel(candidate.status)}</StatusTag>
            <SegmentMeter segments={segmentsOf(candidate, items)} size="lg" />
          </>
        }
        reason={reasonOf(candidate)}
        pager={pager ? <CandidatePager {...pager} /> : null}
      />
      {items.length > 0 ? (
        <MatchBlock candidate={candidate} items={items} focusItemId={focusItemId} />
      ) : null}
      <ClarifyBlock items={clarifyOf(candidate, items)} />
      <HistoryBlock candidate={candidate} items={items} />
      <CompanyBlock candidate={candidate} />
    </EvidenceFrame>
  )
}
