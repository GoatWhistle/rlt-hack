import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import styles from "./styles.module.css"

export function Steps() {
  const { t } = useTranslation()
  const steps = [
    {
      id: "request",
      title: t("upload.steps.request.title"),
      text: t("upload.steps.request.text"),
    },
    {
      id: "products",
      title: t("upload.steps.products.title"),
      text: t("upload.steps.products.text"),
    },
    {
      id: "companies",
      title: t("upload.steps.companies.title"),
      text: t("upload.steps.companies.text"),
    },
    {
      id: "evidence",
      title: t("upload.steps.evidence.title"),
      text: t("upload.steps.evidence.text"),
    },
  ]
  return (
    <section aria-labelledby="steps-title">
      <h2 id="steps-title" className={styles.heading}>
        {t("upload.stepsLabel")}
      </h2>
      <ol className={styles.list}>
        {steps.map((step, index) => (
          <li key={step.id} className={styles.step}>
            <span
              className={clsx(
                styles.number,
                index === 0 && styles.first,
                index === steps.length - 1 && styles.last,
              )}
            >
              {index + 1}
            </span>
            <span className={styles.body}>
              <h3 className={styles.title}>{step.title}</h3>
              <span className={styles.text}>{step.text}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}
