import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import { useCheckReasonText, useInnText } from "@/entities/evidence/labels"
import { CandidateHero } from "@/entities/evidence/ui/candidate-hero"
import { SegmentMeter } from "@/entities/evidence/ui/segment-meter"
import type { Company, Product } from "@/entities/recommendation/model"
import { useFormatters } from "@/shared/i18n/formatters"
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
  const { number } = useFormatters()
  const roleText = useRoleText()
  const innText = useInnText()
  const summaryText = useSummaryText()
  const reasonText = useCheckReasonText()
  const clarifyItems = useClarifyItems()
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
      figure={{
        value: `${number(company.matches.length)}/${number(products.length)}`,
        label: t("compare.match"),
      }}
      verdict={
        <>
          <CompanyStatus company={company} />
          <SegmentMeter segments={companySegments(company, products)} size="lg" />
        </>
      }
    >
      <div className={styles.reason}>
        <h3 className={clsx(styles.reasonTitle, !recommended && styles.warn)}>
          {recommended ? t("evidence.summaryTitle") : t("evidence.checkTitle")}
        </h3>
        <p className={styles.summary}>{summary}</p>
      </div>
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
