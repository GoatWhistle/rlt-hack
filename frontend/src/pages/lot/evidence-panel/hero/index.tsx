import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { Icon } from "@/shared/ui/icon"
import { SegmentMeter } from "../../segment-meter"
import styles from "./styles.module.css"

export type HeroProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function Hero({ company, products }: HeroProps) {
  const { t } = useTranslation("lot")
  const recommended = company.status === "recommended"
  const main = company.clarify[0]
  return (
    <div className={clsx(styles.hero, !recommended && styles.check)}>
      <div className={styles.top}>
        <div className={styles.identity}>
          <h3 className={styles.kicker}>
            {recommended ? t("evidence.summaryTitle") : t("evidence.checkTitle")}
          </h3>
          <h2 className={styles.name}>{company.name}</h2>
          <p className={styles.meta}>
            {company.role} ·{" "}
            <span className={styles.inn}>{t("evidence.inn", { inn: company.inn })}</span>
          </p>
        </div>
        {products.length > 0 ? (
          <span className={styles.score}>
            {company.matches.length}/{products.length}
          </span>
        ) : null}
      </div>
      <p className={styles.summary}>{company.summary}</p>
      <SegmentMeter company={company} products={products} size="lg" />
      {main ? (
        <p className={styles.callout}>
          <Icon name="warning" tone="warning" />
          <span>
            <strong className={styles.calloutLabel}>{t("evidence.mainClarify")}</strong> {main}
          </span>
        </p>
      ) : null}
    </div>
  )
}
