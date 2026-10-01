import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { Recommendation } from "@/entities/recommendation/model"
import { useShortlist } from "@/entities/shortlist/store"
import { EmptyState } from "@/shared/ui/empty-state"
import {
  useWorkspaceView,
  WorkspaceEmpty,
  WorkspaceLayout,
  type WorkspaceView,
} from "@/shared/ui/workspace-layout"
import { CompanyList } from "../company-list"
import { CompareDialog } from "../compare-dialog"
import { EvidencePanel } from "../evidence-panel"
import { ProductList } from "../product-list"
import { ProfilePanel } from "../profile-panel"

export { NARROW_LAYOUT } from "@/shared/ui/workspace-layout"

export type WorkspaceProps = {
  readonly uploadId: string
  readonly lotId: string
  readonly recommendation: Recommendation
}

export function Workspace({ uploadId, lotId, recommendation }: WorkspaceProps) {
  const { t } = useTranslation("lot")
  const { products, companies } = recommendation
  const { narrow, view, show, stackRef } = useWorkspaceView()
  const shortlist = useShortlist(uploadId, lotId)
  const [selectedId, setSelectedId] = useState(companies[0]?.id)
  const [filterId, setFilterId] = useState<string | null>(null)
  const [profileOpen, setProfileOpen] = useState(false)
  const [compareOpen, setCompareOpen] = useState(false)

  const ranks = new Map(companies.map((company, index) => [company.id, index + 1]))
  const filterProduct = products.find((product) => product.id === filterId)
  const shown = filterProduct
    ? companies.filter((company) => company.matches.some((m) => m.productId === filterId))
    : companies
  const selected =
    shown.find((company) => company.id === selectedId) ??
    shown[0] ??
    companies.find((company) => company.id === selectedId)

  function select(id: string) {
    setSelectedId(id)
    if (narrow) show("evidence")
  }

  function filter(productId: string | null) {
    setFilterId(productId)
    if (narrow && productId) show("candidates")
  }

  const productPane = (
    <ProductList
      requestTitle={recommendation.requestTitle}
      products={products}
      filterId={filterId}
      onFilter={filter}
    />
  )
  if (!selected) {
    return (
      <WorkspaceEmpty list={productPane}>
        <EmptyState
          icon="search"
          headingLevel={2}
          title={t("noCandidates.title")}
          description={t("noCandidates.text")}
        />
      </WorkspaceEmpty>
    )
  }

  const labels: Record<WorkspaceView, string> = {
    list: t("views.products"),
    candidates: t("views.companies"),
    evidence: t("views.evidence"),
  }
  return (
    <>
      <WorkspaceLayout
        narrow={narrow}
        legend={t("views.legend")}
        labels={labels}
        view={view}
        onShow={show}
        stackRef={stackRef}
        panes={{
          list: productPane,
          candidates: (
            <CompanyList
              companies={shown}
              ranks={ranks}
              products={products}
              selectedId={selected.id}
              chosen={shortlist.ids}
              filter={
                filterProduct
                  ? { name: filterProduct.name, onReset: () => filter(null) }
                  : undefined
              }
              onSelect={select}
              onCompare={() => setCompareOpen(true)}
            />
          ),
          evidence: (
            <EvidencePanel
              key={selected.id}
              company={selected}
              products={products}
              chosen={shortlist.ids.includes(selected.id)}
              onChoose={() => shortlist.toggle(selected.id)}
              onProfile={() => setProfileOpen(true)}
            />
          ),
        }}
      />
      <ProfilePanel
        open={profileOpen}
        company={selected}
        products={products}
        onClose={() => setProfileOpen(false)}
      />
      <CompareDialog
        open={compareOpen}
        companies={companies.filter((company) => shortlist.ids.includes(company.id))}
        products={products}
        onClose={() => setCompareOpen(false)}
      />
    </>
  )
}
