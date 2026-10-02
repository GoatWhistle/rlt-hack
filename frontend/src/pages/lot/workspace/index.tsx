import { type ReactNode, useState } from "react"
import { useTranslation } from "react-i18next"
import type { Recommendation } from "@/entities/recommendation/model"
import { useShortlist } from "@/entities/shortlist/store"
import { searchDraftPath } from "@/shared/config/paths"
import { useQueryState } from "@/shared/routing/use-query-state"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { Icon } from "@/shared/ui/icon"
import {
  parseView,
  useWorkspaceView,
  viewParam,
  WorkspaceEmpty,
  WorkspaceLayout,
  type WorkspaceView,
} from "@/shared/ui/workspace-layout"
import { CompanyList } from "../company-list"
import { EvidencePanel } from "../evidence-panel"
import { ProductList } from "../product-list"
import { ProfilePanel } from "../profile-panel"

export { NARROW_LAYOUT } from "@/shared/ui/workspace-layout"

export const LOT_PARAMS = ["company", "product", "view"] as const

export type WorkspaceProps = {
  readonly uploadId: string
  readonly lotId: string
  readonly recommendation: Recommendation
  readonly dockAction?: ReactNode
}

export function Workspace({ uploadId, lotId, recommendation, dockAction }: WorkspaceProps) {
  const { t } = useTranslation("lot")
  const { products, companies } = recommendation
  const [params, update] = useQueryState(LOT_PARAMS)
  const view = parseView(params.view)
  const { narrow, stackRef, prepareSwitch } = useWorkspaceView(view)
  const shortlist = useShortlist(uploadId, lotId)
  const [profileOpen, setProfileOpen] = useState(false)

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
          actions={
            <ButtonLink variant="secondary" to={searchDraftPath(recommendation.requestTitle)}>
              <Icon name="search" />
              {t("noCandidates.search")}
            </ButtonLink>
          }
        />
      </WorkspaceEmpty>
    )
  }

  const position = shown.findIndex((company) => company.id === selected.id)
  const neighbour = (step: number) => {
    const target = shown[position + step]
    return position >= 0 && target ? () => update({ company: target.id }) : undefined
  }
  return (
    <>
      <WorkspaceLayout
        narrow={narrow}
        legend={t("views.legend")}
        labels={{
          list: t("views.products"),
          candidates: t("views.companies"),
          evidence: t("views.evidence"),
        }}
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
            />
          ),
          evidence: (
            <EvidencePanel
              company={selected}
              products={products}
              chosen={shortlist.ids.includes(selected.id)}
              extraAction={dockAction}
              pager={
                narrow && position >= 0
                  ? {
                      index: position + 1,
                      total: shown.length,
                      onPrev: neighbour(-1),
                      onNext: neighbour(1),
                    }
                  : undefined
              }
              onChoose={() => shortlist.toggle(selected.id)}
              onProfile={() => setProfileOpen(true)}
            />
          ),
        }}
        view={view}
        onShow={show}
        stackRef={stackRef}
      />
      <ProfilePanel
        open={profileOpen}
        company={selected}
        products={products}
        choice={{
          chosen: shortlist.ids.includes(selected.id),
          onToggle: () => shortlist.toggle(selected.id),
        }}
        onClose={() => setProfileOpen(false)}
      />
    </>
  )
}
