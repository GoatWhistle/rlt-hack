import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useLocation } from "react-router"
import type { Recommendation } from "@/entities/recommendation/model"
import { parseRecommendation } from "@/entities/recommendation/parse"
import { ButtonLink } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { EmptyState } from "@/shared/ui/empty-state"
import { Stack } from "@/shared/ui/stack"
import { ChainBar } from "./chain-bar"
import { CompanyList } from "./company-list"
import { EvidencePanel } from "./evidence-panel"
import { ProductList } from "./product-list"
import styles from "./styles.module.css"

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

  return (
    <div className={styles.page}>
      <Stack>
        <Caption>
          {recommendation.fileName} · {recommendation.lotLabel}
        </Caption>
        <h1 className={styles.title}>{recommendation.requestTitle}</h1>
      </Stack>
      <ChainBar recommendation={recommendation} selected={selected} />
      <div className={styles.columns}>
        <ProductList products={recommendation.products} />
        <CompanyList
          companies={recommendation.companies}
          totalProducts={recommendation.products.length}
          selectedId={selected.id}
          onSelect={setSelectedId}
        />
        <EvidencePanel company={selected} products={recommendation.products} />
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
