import { useTranslation } from "react-i18next"
import { useCompanyName, useRoleLabel } from "@/entities/evidence/labels"
import type { Candidate, QueryItem } from "@/entities/search/model"
import { CoverageMatrix } from "@/entities/search/ui/coverage-matrix"
import { Dialog } from "@/shared/ui/dialog"
import { type Fact, FactList } from "@/shared/ui/fact-list"

export type CompareDialogProps = {
  readonly open: boolean
  readonly candidates: readonly Candidate[]
  readonly items: readonly QueryItem[]
  readonly onClose: () => void
}

export function CompareDialog({ open, candidates, items, onClose }: CompareDialogProps) {
  const { t } = useTranslation("search")
  const { t: evidence } = useTranslation("evidence")
  const roleLabel = useRoleLabel()
  const nameOf = useCompanyName()
  const facts: Fact[] = candidates.map((candidate) => ({
    key: candidate.id,
    term: nameOf(candidate),
    value: [
      roleLabel(candidate.role),
      evidence(`roleBasis.${candidate.roleContext.basis}`),
      evidence(`novelty.${candidate.novelty}`),
    ].join(" · "),
  }))
  return (
    <Dialog open={open} title={t("compare.title")} onClose={onClose} size="wide">
      <CoverageMatrix candidates={candidates} items={items} />
      <FactList facts={facts} />
    </Dialog>
  )
}
