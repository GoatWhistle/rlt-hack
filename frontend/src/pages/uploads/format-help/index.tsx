import { useTranslation } from "react-i18next"
import { KNOWN_COLUMNS, REQUIRED_COLUMNS } from "@/entities/notice/model"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export const SAMPLE_PATH = "/notices-sample.csv"

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
      <a href={SAMPLE_PATH} download className={styles.sample}>
        <Icon name="download" />
        {t("intro.sample")}
      </a>
    </section>
  )
}
