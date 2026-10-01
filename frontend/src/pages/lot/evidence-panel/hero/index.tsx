import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Icon } from "@/shared/ui/icon"
import { StatusTag } from "../../company-list"
import { SegmentMeter } from "../../segment-meter"
import { useRoleText } from "../../status"
import styles from "./styles.module.css"

export type HeroProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function Hero({ company, products }: HeroProps) {
  const { t } = useTranslation("lot")
  const { number } = useFormatters()
  const roleText = useRoleText()
  const recommended = company.status === "recommended"
  const main = company.clarify[0]
  return (
    <div className={clsx(styles.hero, company.status === "check" && styles.check)}>
      <div className={styles.top}>
        <div className={styles.identity}>
          <h2 className={styles.name}>{company.name}</h2>
          <p className={styles.meta}>
            {roleText(company)} ·{" "}
            <span className={styles.inn}>{t("evidence.inn", { inn: company.inn })}</span>
          </p>
        </div>
        {products.length > 0 ? (
          <p className={styles.result}>
            <span className={styles.score}>
              {number(company.matches.length)}/{number(products.length)}
            </span>
            <span className={styles.scoreLabel}>{t("compare.match")}</span>
          </p>
        ) : null}
      </div>
      <div className={styles.verdict}>
        <StatusTag company={company} />
        <SegmentMeter company={company} products={products} size="lg" />
      </div>
      <div className={styles.reason}>
        <h3 className={styles.reasonTitle}>
          {recommended ? t("evidence.summaryTitle") : t("evidence.checkTitle")}
        </h3>
        <p className={styles.summary}>{company.summary}</p>
      </div>
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
