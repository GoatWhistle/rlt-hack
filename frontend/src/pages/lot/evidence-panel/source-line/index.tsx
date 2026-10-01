import { useTranslation } from "react-i18next"
import type { Source } from "@/entities/recommendation/model"
import { useFormatters } from "@/shared/i18n/formatters"
import styles from "./styles.module.css"

export function SourceLine({ source }: { readonly source?: Source }) {
  const { t } = useTranslation("lot")
  const { date } = useFormatters()
  if (!source) return <span className={styles.missing}>{t("evidence.noSource")}</span>
  return (
    <span className={styles.line}>
      <span className={styles.kind}>{t(`evidence.sourceKind.${source.kind}`)}</span>
      <a href={source.url} className={styles.link}>
        {source.title}
      </a>
      {source.checkedAt ? (
        <span>{t("evidence.checkedAt", { date: date(source.checkedAt) })}</span>
      ) : null}
    </span>
  )
}
