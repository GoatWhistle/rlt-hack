import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { Recommendation } from "@/entities/recommendation/model"
import { useShortlist } from "@/entities/shortlist/store"
import { useQueryState } from "@/shared/routing/use-query-state"
import { EmptyState } from "@/shared/ui/empty-state"
import {
  parseView,
  useWorkspaceView,
  viewParam,
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

export const LOT_PARAMS = ["company", "product", "view"] as const

export type WorkspaceProps = {
  readonly uploadId: string
  readonly lotId: string
  readonly recommendation: Recommendation
}

export function Workspace({ uploadId, lotId, recommendation }: WorkspaceProps) {
  const { t } = useTranslation("lot")
  const { products, companies } = recommendation
  const [params, update] = useQueryState(LOT_PARAMS)
  const view = parseView(params.view)
  const { narrow, stackRef, prepareSwitch } = useWorkspaceView(view)
  const shortlist = useShortlist(uploadId, lotId)
  const [profileOpen, setProfileOpen] = useState(false)
  const [compareOpen, setCompareOpen] = useState(false)

  const ranks = new Map(companies.map((company, index) => [company.id, index + 1]))
  const filterProduct = products.find((product) => product.id === params.product)
  const filterId = filterProduct?.id ?? null
  const shown = filterProduct
    ? companies.filter((company) => company.matches.some((m) => m.productId === filterId))
    : companies
  const selected =
    shown.find((company) => company.id === params.company) ??
    shown[0] ??
    companies.find((company) => company.id === params.company) ??
    companies[0]

  function show(next: WorkspaceView) {
    prepareSwitch(false)
    update({ view: viewParam(next) })
  }

  function select(id: string) {
    if (narrow) prepareSwitch(true)
    update({ company: id, ...(narrow ? { view: viewParam("evidence") } : {}) })
  }

  function filter(productId: string | null) {
    const move = narrow && productId !== null
    if (move) prepareSwitch(true)
    update({ product: productId, ...(move ? { view: viewParam("candidates") } : {}) })
  }

  const productPane = <ProductList products={products} filterId={filterId} onFilter={filter} />
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
    candidates: t("views.candidates"),
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
