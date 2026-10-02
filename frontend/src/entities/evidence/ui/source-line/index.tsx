import { useTranslation } from "react-i18next"
import type { Source } from "@/entities/evidence/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Icon } from "@/shared/ui/icon"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export type SourceLineProps = {
  readonly source?: Source
  readonly stale?: boolean
}

export function SourceLine({ source, stale = false }: SourceLineProps) {
  const { t } = useTranslation("evidence")
  const { date } = useFormatters()
  if (!source) return <span className={styles.missing}>{t("noSource")}</span>
  return (
    <span className={styles.line}>
      <span>{t(`sourceKind.${source.kind}`)}</span>
      <a href={source.url} target="_blank" rel="noopener noreferrer" className={styles.link}>
        {source.title}
        <span className={styles.external} aria-hidden="true">
          <Icon name="external" size="sm" />
        </span>{" "}
        <VisuallyHidden>{t("newTab")}</VisuallyHidden>
      </a>
      {source.checkedAt ? (
        <span className={stale ? styles.stale : undefined}>
          {t(
            source.kind === "purchase"
              ? "purchaseDate"
              : stale
                ? "offer.staleCheck"
                : "checkedAt",
            { date: date(source.checkedAt) },
          )}
        </span>
      ) : null}
    </span>
  )
}
