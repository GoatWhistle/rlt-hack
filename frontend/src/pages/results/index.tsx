import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useLocation } from "react-router"
import type { Recommendation } from "@/entities/recommendation/model"
import { parseRecommendation } from "@/entities/recommendation/parse"
import { ButtonLink } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { EmptyState } from "@/shared/ui/empty-state"
import { CompanyList } from "./company-list"
import { EvidencePanel } from "./evidence-panel"
import { ProductList } from "./product-list"
import { ResultHeader } from "./result-header"
import styles from "./styles.module.css"

export const STACKED_LAYOUT = "(max-width: 64rem)"

function readRecommendation(state: unknown): Recommendation | null {
  try {
    return parseRecommendation(state)
  } catch {
    return null
  }
}

export function ResultsPage() {
  const { t } = useTranslation()
  const location = useLocation()
  const [recommendation] = useState(() => readRecommendation(location.state))
  const [selectedId, setSelectedId] = useState(recommendation?.companies[0]?.id)
  const grounds = useRef<HTMLDivElement>(null)
  const selected =
    recommendation?.companies.find((company) => company.id === selectedId) ??
    recommendation?.companies[0]

  if (!recommendation || !selected) {
    return (
      <EmptyState
        title={t("results.empty.title")}
        description={t("results.empty.description")}
        actions={<ButtonLink to="/">{t("results.empty.action")}</ButtonLink>}
      />
    )
  }

  function select(id: string) {
    setSelectedId(id)
    if (window.matchMedia?.(STACKED_LAYOUT).matches) {
      grounds.current?.scrollIntoView({ block: "start" })
    }
  }

  return (
    <div className={styles.page}>
      <ResultHeader recommendation={recommendation} />
      <div className={styles.columns}>
        <ProductList products={recommendation.products} />
        <CompanyList
          companies={recommendation.companies}
          products={recommendation.products}
          selectedId={selected.id}
          onSelect={select}
        />
        <div ref={grounds} className={styles.grounds}>
          <EvidencePanel
            key={selected.id}
            company={selected}
            products={recommendation.products}
          />
        </div>
      </div>
      <div className={styles.footer}>
        <Caption muted>{t("results.demoNote")}</Caption>
        <ButtonLink to="/" variant="secondary">
          {t("results.newFile")}
        </ButtonLink>
      </div>
    </div>
  )
}
