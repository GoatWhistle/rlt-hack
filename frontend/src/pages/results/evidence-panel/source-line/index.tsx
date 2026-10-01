import { useTranslation } from "react-i18next"
import type { Source } from "@/entities/recommendation/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import styles from "./styles.module.css"

export function SourceLine({ source }: { readonly source?: Source }) {
  const { t } = useTranslation()
  const { date } = useFormatters()
  if (!source) return <Caption muted>{t("results.evidence.noSource")}</Caption>
  return (
    <span className={styles.line}>
      <span className={styles.kind}>{t(`results.evidence.sourceKind.${source.kind}`)}</span>
      <a href={source.url} className={styles.link}>
        {source.title}
      </a>
      {source.checkedAt ? (
        <span>{t("results.evidence.checkedAt", { date: date(source.checkedAt) })}</span>
      ) : null}
    </span>
  )
}
