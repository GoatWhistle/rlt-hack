import { useTranslation } from "react-i18next"
import { useCheckReasonText, useInnText, useMatchFigure } from "@/entities/evidence/labels"
import { CandidateHero } from "@/entities/evidence/ui/candidate-hero"
import { SegmentMeter } from "@/entities/evidence/ui/segment-meter"
import type { Company, Product } from "@/entities/recommendation/model"
import { Icon } from "@/shared/ui/icon"
import { CompanyStatus } from "../../company-list"
import { companySegments, useClarifyItems, useRoleText, useSummaryText } from "../../status"
import styles from "./styles.module.css"

export type HeroProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function Hero({ company, products }: HeroProps) {
  const { t } = useTranslation("lot")
  const roleText = useRoleText()
  const innText = useInnText()
  const summaryText = useSummaryText()
  const reasonText = useCheckReasonText()
  const clarifyItems = useClarifyItems()
  const figureOf = useMatchFigure()
  const recommended = company.status === "recommended"
  const reasons = recommended ? [] : company.checkReasons.map(reasonText)
  const summary =
    reasons.length > 0 ? reasons.join(" ") : summaryText(company) || t("evidence.noHighlights")
  const main = clarifyItems(company, products)[0]
  return (
    <CandidateHero
      name={company.name}
      role={roleText(company)}
      code={innText(company.inn)}
      check={!recommended}
      figure={{ ...figureOf(company.matches, products.length), label: t("compare.match") }}
      verdict={
        <>
          <CompanyStatus company={company} />
          <SegmentMeter segments={companySegments(company, products)} size="lg" />
        </>
      }
      reason={{
        title: recommended ? t("evidence.summaryTitle") : t("evidence.checkTitle"),
        text: summary,
      }}
    >
      {main ? (
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
