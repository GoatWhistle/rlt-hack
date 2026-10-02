import { useTranslation } from "react-i18next"
import { KNOWN_COLUMNS, REQUIRED_COLUMNS } from "@/entities/notice/model"
import { NOTICES_SAMPLE_PATH } from "@/shared/config/paths"
import { DownloadLink } from "@/shared/ui/download-link"
import styles from "./styles.module.css"

export const SAMPLE_PATH = NOTICES_SAMPLE_PATH

const OPTIONAL_COLUMNS = KNOWN_COLUMNS.filter(
  (column) => !(REQUIRED_COLUMNS as readonly string[]).includes(column),
)

export function FormatHelp() {
  const { t } = useTranslation("uploads")
  return (
    <section className={styles.format} aria-labelledby="format-title">
      <h2 id="format-title" className={styles.title}>
        {t("intro.format")}
      </h2>
      <p className={styles.text}>{t("intro.formatText")}</p>
      <dl className={styles.columns}>
        <dt className={styles.term}>{t("intro.required")}</dt>
        <dd className={styles.codes}>{REQUIRED_COLUMNS.join(", ")}</dd>
        <dt className={styles.term}>{t("intro.optional")}</dt>
        <dd className={styles.codes}>{OPTIONAL_COLUMNS.join(", ")}</dd>
      </dl>
      <DownloadLink href={SAMPLE_PATH}>{t("intro.sample")}</DownloadLink>
    </section>
  )
}
