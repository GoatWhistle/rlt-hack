import { useTranslation } from "react-i18next"
import { CandidateHero } from "@/entities/evidence/ui/candidate-hero"
import type { Company, Product } from "@/entities/recommendation/model"
import { Icon } from "@/shared/ui/icon"
import { SegmentMeter } from "../../segment-meter"
import { RankingReasons } from "../ranking-reasons"
import styles from "./styles.module.css"

export type HeroProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

function useReasonTitle(company: Company): string {
  const { t } = useTranslation("lot")
  if (company.status === "historical") return t("history.whyFound")
  return company.status === "recommended"
    ? t("evidence.summaryTitle")
    : t("evidence.checkTitle")
}

export function Hero({ company, products }: HeroProps) {
  const { t } = useTranslation("lot")
  const title = useReasonTitle(company)
  const main = company.clarify[0]
  return (
    <CandidateHero
      name={company.name}
      role={company.role}
      code={t("evidence.inn", { inn: company.inn })}
      check={company.status === "check"}
      figure={
        products.length > 0
          ? {
              value: `${company.matches.length}/${products.length}`,
              label: t("compare.match"),
            }
          : undefined
      }
      verdict={<SegmentMeter company={company} products={products} size="lg" />}
      reason={{ title, text: company.summary }}
    >
      <RankingReasons company={company} />
      {main && company.status !== "historical" && !company.history ? (
        <p className={styles.callout}>
          <Icon name="warning" tone="warning" />
          <span>
            <strong className={styles.calloutLabel}>{t("evidence.mainClarify")}</strong> {main}
          </span>
        </p>
      ) : null}
    </CandidateHero>
  )
}
