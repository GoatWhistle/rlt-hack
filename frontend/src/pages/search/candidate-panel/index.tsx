import { useTranslation } from "react-i18next"
import { useInnText, useRoleLabel, useStatusLabel } from "@/entities/evidence/labels"
import { CandidateHero } from "@/entities/evidence/ui/candidate-hero"
import { EvidenceAction, EvidenceFrame } from "@/entities/evidence/ui/evidence-frame"
import { SegmentMeter } from "@/entities/evidence/ui/segment-meter"
import { StatusTag } from "@/entities/evidence/ui/status-tag"
import type { Candidate, QueryItem } from "@/entities/search/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { candidateSegments } from "../labels"
import { CompanyBlock } from "./company-block"
import { HeroFacts } from "./hero-facts"
import { HistoryBlock } from "./history-block"
import { MatchBlock } from "./match-block"

export type CandidatePanelProps = {
  readonly candidate: Candidate
  readonly items: readonly QueryItem[]
  readonly onProfile: () => void
}

export function CandidatePanel({ candidate, items, onProfile }: CandidatePanelProps) {
  const { t } = useTranslation("search")
  const { number } = useFormatters()
  const roleLabel = useRoleLabel()
  const statusLabel = useStatusLabel()
  const innText = useInnText()
  return (
    <EvidenceFrame
      label={candidate.name}
      actions={
        <EvidenceAction
          variant="secondary"
          label={t("evidence.profile")}
          shortLabel={t("evidence.profileShort")}
          onClick={onProfile}
        />
      }
    >
      <CandidateHero
        name={candidate.name}
        role={roleLabel(candidate.role)}
        code={innText(candidate.inn)}
        check={candidate.status === "check"}
        figure={{
          value: `${number(candidate.matches.length)}/${number(items.length)}`,
          label: t("views.items"),
        }}
        verdict={
          <>
            <StatusTag status={candidate.status}>{statusLabel(candidate.status)}</StatusTag>
            <SegmentMeter segments={candidateSegments(candidate, items)} size="lg" />
          </>
        }
      >
        <HeroFacts candidate={candidate} />
      </CandidateHero>
      <MatchBlock candidate={candidate} items={items} />
      <HistoryBlock history={candidate.history} items={items} />
      <CompanyBlock candidate={candidate} />
    </EvidenceFrame>
  )
}
