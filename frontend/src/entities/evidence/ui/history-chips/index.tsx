import { Trans, useTranslation } from "react-i18next"
import { MetaChip, MetaChips } from "@/shared/ui/meta-chip"

export type HistoryChipsProps = {
  readonly similar: number
  readonly wins: number
}

export function HistoryChips({ similar, wins }: HistoryChipsProps) {
  const { t } = useTranslation("candidate")
  if (similar <= 0 && wins <= 0) {
    return (
      <MetaChips>
        <MetaChip tone="muted">{t("card.noHistory")}</MetaChip>
      </MetaChips>
    )
  }
  return (
    <MetaChips>
      {similar > 0 ? (
        <MetaChip>
          <Trans t={t} i18nKey="card.similar" count={similar} components={{ b: <b /> }} />
        </MetaChip>
      ) : null}
      {wins > 0 ? (
        <MetaChip tone="accent">
          <Trans t={t} i18nKey="card.wins" count={wins} components={{ b: <b /> }} />
        </MetaChip>
      ) : null}
    </MetaChips>
  )
}
