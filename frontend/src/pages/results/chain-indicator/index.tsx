import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export function ChainIndicator() {
  const { t } = useTranslation()
  const steps = [
    t("results.chain.request"),
    t("results.chain.products"),
    t("results.chain.companies"),
    t("results.chain.evidence"),
  ]
  return (
    <ol className={styles.chain} aria-label={t("results.chain.label")}>
      {steps.map((step, index) => (
        <li key={step} className={styles.step}>
          {index > 0 ? <Icon name="chevron" size="sm" /> : null}
          {step}
        </li>
      ))}
    </ol>
  )
}
