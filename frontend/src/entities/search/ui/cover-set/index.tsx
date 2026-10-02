import { useTranslation } from "react-i18next"
import { useCompanyName } from "@/entities/evidence/labels"
import { coverSet } from "@/entities/search/coverage"
import type { Candidate, QueryItem } from "@/entities/search/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import styles from "./styles.module.css"

export type CoverSetNoteProps = {
  readonly candidates: readonly Candidate[]
  readonly items: readonly QueryItem[]
}

export function CoverSetNote({ candidates, items }: CoverSetNoteProps) {
  const { t } = useTranslation("search")
  const { list } = useFormatters()
  const nameOf = useCompanyName()
  if (items.length < 2) return null
  const set = coverSet(candidates, items)
  const names = new Map(items.map((item) => [item.id, item.name]))
  const named = (ids: readonly string[]) => list(ids.map((id) => names.get(id) ?? id))
  return (
    <section className={styles.cover} aria-label={t("cover.title")}>
      <h3 className={styles.title}>{t("cover.title")}</h3>
      <ul className={styles.picks}>
        {set.picks.map((pick) => (
          <li key={pick.candidate.id}>
            <span className={styles.name}>{nameOf(pick.candidate)}</span>
            {pick.confirmed.length > 0
              ? ` ${t("cover.confirmed", { items: named(pick.confirmed) })}`
              : ""}
            {pick.toClarify.length > 0
              ? ` ${t("cover.toClarify", { items: named(pick.toClarify) })}`
              : ""}
          </li>
        ))}
      </ul>
      {set.gaps.length > 0 ? (
        <p className={styles.gap}>{t("cover.gaps", { items: named(set.gaps) })}</p>
      ) : null}
      {set.overlaps.length > 0 ? (
        <Caption>{t("cover.overlaps", { items: named(set.overlaps) })}</Caption>
      ) : null}
      <Caption>{t("cover.disclaimer")}</Caption>
    </section>
  )
}
