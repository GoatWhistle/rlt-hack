import { useTranslation } from "react-i18next"
import { useCheckReasonText, useHighlightText } from "@/entities/evidence/labels"
import type { Candidate } from "@/entities/search/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Icon } from "@/shared/ui/icon"
import { ScoreBar } from "@/shared/ui/score-bar"
import styles from "./styles.module.css"

export function HeroFacts({ candidate }: { readonly candidate: Candidate }) {
  const { t } = useTranslation("search")
  const { number } = useFormatters()
  const highlightText = useHighlightText()
  const reasonText = useCheckReasonText()
  return (
    <>
      <ScoreBar
        showLabel
        value={candidate.score.total}
        label={t("candidates.score")}
        valueText={t("candidates.scoreValue", { value: number(candidate.score.total) })}
      />
      {candidate.checkReasons.length > 0 ? (
        <section className={styles.reasons}>
          <h3 className={styles.title}>{t("evidence.checkTitle")}</h3>
          <ul className={styles.list}>
            {candidate.checkReasons.map((reason) => (
              <li key={reason} className={styles.reason}>
                <Icon name="warning" size="sm" tone="warning" />
                <span>{reasonText(reason)}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {candidate.highlights.length > 0 ? (
        <section className={styles.group}>
          <h3 className={styles.title}>{t("evidence.highlightsTitle")}</h3>
          <ul className={styles.list}>
            {candidate.highlights.map((highlight) => (
              <li key={highlight.code} className={styles.highlight}>
                <Icon name="check" size="sm" tone="confirmed" />
                <span>{highlightText(highlight)}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </>
  )
}
