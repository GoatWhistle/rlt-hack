import { useTranslation } from "react-i18next"
import type { MatchBasis } from "@/entities/evidence/model"
import { BasisMarker } from "@/entities/evidence/ui/match-row"
import { Caption } from "@/shared/ui/caption"
import { ResultSection } from "@/shared/ui/result-section"
import styles from "./styles.module.css"

export const GUIDE_ROWS = ["stock", "catalog", "inferred", "none"] as const

export function ReadingGuide() {
  const { t } = useTranslation("search")
  const { t: evidence } = useTranslation("evidence")
  return (
    <ResultSection framed title={t("guide.title")}>
      <div className={styles.body}>
        <ul className={styles.list}>
          {GUIDE_ROWS.map((row) => (
            <li key={row} className={styles.row}>
              <BasisMarker basis={row === "none" ? undefined : (row satisfies MatchBasis)} />
              <span className={styles.text}>
                <span className={styles.term}>
                  {row === "none" ? evidence("notFound") : evidence(`basis.${row}`)}
                </span>
                <span>{t(`guide.${row}`)}</span>
              </span>
            </li>
          ))}
        </ul>
        <Caption>{t("guide.decision")}</Caption>
      </div>
    </ResultSection>
  )
}
