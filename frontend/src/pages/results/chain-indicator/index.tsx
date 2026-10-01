import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export function ChainIndicator() {
  const { t } = useTranslation()
  const done = [
    t("results.chain.request"),
    t("results.chain.products"),
    t("results.chain.companies"),
  ]
  return (
    <ol className={styles.chain} aria-label={t("results.chain.label")}>
      {done.map((step) => (
        <li key={step} className={styles.step}>
          <span className={styles.done}>
            <Icon name="check" size="sm" />
          </span>
          {step}
          <span className={styles.link} aria-hidden="true" />
        </li>
      ))}
      <li className={styles.current} aria-current="step">
        <span className={styles.marker} aria-hidden="true" />
        {t("results.chain.evidence")}
      </li>
    </ol>
  )
}
