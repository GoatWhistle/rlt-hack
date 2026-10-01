import { useTranslation } from "react-i18next"
import {
  useCheckReasonText,
  useHighlightText,
  useInnText,
  useMatchFigure,
  useRoleLabel,
  useStatusLabel,
} from "@/entities/evidence/labels"
import { CandidateHero, type HeroReason } from "@/entities/evidence/ui/candidate-hero"
import { EvidenceAction, EvidenceFrame } from "@/entities/evidence/ui/evidence-frame"
import { SegmentMeter } from "@/entities/evidence/ui/segment-meter"
import { StatusTag } from "@/entities/evidence/ui/status-tag"
import type { Candidate, QueryItem } from "@/entities/search/model"
import { Icon } from "@/shared/ui/icon"
import { candidateSegments } from "../labels"
import { CompanyBlock } from "./company-block"
import { HistoryBlock } from "./history-block"
import { MatchBlock } from "./match-block"

export const SUMMARY_SEPARATOR = " · "

export type CandidatePanelProps = {
  readonly candidate: Candidate
  readonly items: readonly QueryItem[]
  readonly chosen: boolean
  readonly onChoose: () => void
  readonly onProfile: () => void
}

function useReason(): (candidate: Candidate) => HeroReason {
  const { t } = useTranslation("search")
  const highlightText = useHighlightText()
  const reasonText = useCheckReasonText()
  return (candidate) => {
    if (candidate.status === "check") {
      return {
        title: t("evidence.checkTitle"),
        text: candidate.checkReasons.map(reasonText).join(" ") || t("evidence.noHighlights"),
      }
    }
    const highlights = candidate.highlights.map(highlightText)
    return {
      title: t("evidence.summaryTitle"),
      text:
        highlights.length > 0 ? highlights.join(SUMMARY_SEPARATOR) : t("evidence.noHighlights"),
    }
  }
}

export function CandidatePanel({
  candidate,
  items,
  chosen,
  onChoose,
  onProfile,
}: CandidatePanelProps) {
  const { t } = useTranslation("search")
  const roleLabel = useRoleLabel()
  const statusLabel = useStatusLabel()
  const innText = useInnText()
  const figureOf = useMatchFigure()
  const reasonOf = useReason()
  return (
    <EvidenceFrame
      label={candidate.name}
      actions={
        <>
          <EvidenceAction
            variant={chosen ? "secondary" : "primary"}
            icon={chosen ? <Icon name="check" /> : null}
            label={chosen ? t("evidence.chosen") : t("evidence.choose")}
            onClick={onChoose}
          />
          <EvidenceAction
            variant="secondary"
            label={t("evidence.profile")}
            shortLabel={t("evidence.profileShort")}
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
        figure={{ ...figureOf(candidate.matches, items.length), label: t("evidence.figure") }}
        verdict={
          <>
            <StatusTag status={candidate.status}>{statusLabel(candidate.status)}</StatusTag>
            <SegmentMeter segments={candidateSegments(candidate, items)} size="lg" />
          </>
        }
        reason={reasonOf(candidate)}
      />
      <MatchBlock candidate={candidate} items={items} />
      <HistoryBlock history={candidate.history} items={items} />
      <CompanyBlock candidate={candidate} />
    </EvidenceFrame>
  )
}
