import { useTranslation } from "react-i18next"
import { Caption } from "@/shared/ui/caption"
import { Stack } from "@/shared/ui/stack"
import styles from "./styles.module.css"

export function Steps() {
  const { t } = useTranslation()
  const steps = [
    { id: "01", title: t("upload.steps.request.title"), text: t("upload.steps.request.text") },
    {
      id: "02",
      title: t("upload.steps.products.title"),
      text: t("upload.steps.products.text"),
    },
    {
      id: "03",
      title: t("upload.steps.companies.title"),
      text: t("upload.steps.companies.text"),
    },
    {
      id: "04",
      title: t("upload.steps.evidence.title"),
      text: t("upload.steps.evidence.text"),
    },
  ]
  return (
    <section className={styles.section} aria-labelledby="steps-title">
      <h2 id="steps-title" className={styles.heading}>
        {t("upload.stepsLabel")}
      </h2>
      <ol className={styles.list}>
        {steps.map((step) => (
          <Stack key={step.id} as="li">
            <Caption muted>{step.id}</Caption>
            <h3 className={styles.title}>{step.title}</h3>
            <p className={styles.text}>{step.text}</p>
          </Stack>
        ))}
      </ol>
    </section>
  )
}
