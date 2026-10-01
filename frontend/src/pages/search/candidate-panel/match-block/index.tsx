import { useTranslation } from "react-i18next"
import { BASIS_ORDER, MatchRow } from "@/entities/evidence/ui/match-row"
import { type Candidate, matchOf, type QueryItem } from "@/entities/search/model"
import { Caption } from "@/shared/ui/caption"
import { PanelBlock } from "@/shared/ui/panel-block"
import { Stack } from "@/shared/ui/stack"

const MISSING = Object.keys(BASIS_ORDER).length

export type MatchBlockProps = {
  readonly candidate: Candidate
  readonly items: readonly QueryItem[]
}

export function MatchBlock({ candidate, items }: MatchBlockProps) {
  const { t } = useTranslation("search")
  const rows = items
    .map((item) => ({ item, match: matchOf(candidate, item.id) }))
    .sort(
      (a, b) =>
        (a.match ? BASIS_ORDER[a.match.basis] : MISSING) -
        (b.match ? BASIS_ORDER[b.match.basis] : MISSING),
    )
  return (
    <PanelBlock
      title={t("evidence.matchesTitle")}
      aside={t("evidence.matchesAside", {
        matched: candidate.matches.length,
        total: items.length,
      })}
    >
      <Stack as="ul">
        {rows.map(({ item, match }) => (
          <li key={item.id}>
            <MatchRow name={item.name} basis={match?.basis} source={match?.source} />
          </li>
        ))}
      </Stack>
      <Caption>{t("evidence.matchesHint")}</Caption>
    </PanelBlock>
  )
}
