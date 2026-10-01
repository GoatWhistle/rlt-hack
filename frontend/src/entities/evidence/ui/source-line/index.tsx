import { useTranslation } from "react-i18next"
import type { Source } from "@/entities/evidence/model"
import { useFormatters } from "@/shared/i18n/formatters"
import styles from "./styles.module.css"

export function SourceLine({ source }: { readonly source?: Source }) {
  const { t } = useTranslation("evidence")
  const { date } = useFormatters()
  if (!source) return <span className={styles.missing}>{t("noSource")}</span>
  return (
    <span className={styles.line}>
      <span className={styles.kind}>{t(`sourceKind.${source.kind}`)}</span>
      <a href={source.url} className={styles.link}>
        {source.title}
      </a>
      {source.checkedAt ? (
        <span>{t("checkedAt", { date: date(source.checkedAt) })}</span>
      ) : null}
    </span>
  )
}
