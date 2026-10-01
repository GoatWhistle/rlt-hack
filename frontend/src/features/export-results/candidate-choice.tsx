import { type ReactElement, useState } from "react"
import { useTranslation } from "react-i18next"
import { RadioGroup } from "@/shared/ui/radio-group"

export type CandidateScope = "all" | "shortlist"

export type CandidateChoice = {
  readonly scope: CandidateScope
  readonly field: ReactElement
  readonly reset: () => void
}

export function useCandidateChoice(chosen: number, emptyHint: string): CandidateChoice {
  const { t } = useTranslation("export")
  const [picked, setPicked] = useState<CandidateScope | null>(null)
  const scope: CandidateScope = chosen === 0 ? "all" : (picked ?? "shortlist")
  const field = (
    <RadioGroup
      legend={t("candidates.legend")}
      options={[
        { value: "all", label: t("candidates.all") },
        {
          value: "shortlist",
          label: t("candidates.shortlist", { count: chosen }),
          disabled: chosen === 0,
          hint: chosen === 0 ? emptyHint : undefined,
        },
      ]}
      value={scope}
      onChange={setPicked}
    />
  )
  return { scope, field, reset: () => setPicked(null) }
}
