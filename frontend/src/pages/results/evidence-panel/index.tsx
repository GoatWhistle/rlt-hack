import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { Icon, type IconName, type IconTone } from "@/shared/ui/icon"
import { Tag } from "@/shared/ui/tag"
import { ResultSection } from "../section"
import styles from "./styles.module.css"

type BlockProps = {
  readonly title: string
  readonly icon: IconName
  readonly tone: IconTone
  readonly children: ReactNode
}

function Block({ title, icon, tone, children }: BlockProps) {
  return (
    <div className={styles.block}>
      <h3 className={styles.blockTitle}>
        <Icon name={icon} tone={tone} />
        {title}
      </h3>
      {children}
    </div>
  )
}

function Points({ items }: { readonly items: readonly string[] }) {
  return (
    <ul className={styles.points}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

export type EvidencePanelProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function EvidencePanel({ company, products }: EvidencePanelProps) {
  const { t } = useTranslation()
  return (
    <ResultSection title={t("results.evidence.title")} width="wide">
      <div className={styles.panel}>
        <div className={styles.head}>
          <div className={styles.company}>
            <span className={styles.name}>{company.name}</span>
            <Caption>{company.role}</Caption>
          </div>
          <ul className={styles.coverage} aria-label={t("results.evidence.coverage")}>
            {products.map((product) => {
              const covered = company.coveredProductIds.includes(product.id)
              return (
                <Tag key={product.id} as="li" tone={covered ? "solid" : "tentative"}>
                  <Icon
                    name={covered ? "check" : "minus"}
                    tone={covered ? "confirmed" : "current"}
                    size="sm"
                    label={t(covered ? "results.evidence.covered" : "results.evidence.missing")}
                  />
                  {product.name}
                </Tag>
              )
            })}
          </ul>
        </div>
        <Block title={t("results.evidence.why")} icon="checkCircle" tone="confirmed">
          <Points items={company.why} />
        </Block>
        <Block title={t("results.evidence.proof")} icon="link" tone="source">
          <ul className={styles.sources}>
            {company.evidence.map((source) => (
              <li key={source.title} className={styles.source}>
                <span className={styles.kind}>{source.kind}</span>
                <span className={styles.sourceBody}>
                  <a href={source.url} className={styles.link}>
                    {source.title}
                  </a>
                  <Caption>{source.meta}</Caption>
                </span>
              </li>
            ))}
          </ul>
        </Block>
        <Block title={t("results.evidence.clarify")} icon="warning" tone="current">
          <Points items={company.clarify} />
        </Block>
      </div>
      <div className={styles.actions}>
        <Button>{t("results.evidence.shortlist")}</Button>
        <Button variant="secondary">{t("results.evidence.exclude")}</Button>
      </div>
    </ResultSection>
  )
}
