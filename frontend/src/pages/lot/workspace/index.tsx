import { clsx } from "clsx"
import { type ReactElement, useState } from "react"
import { useTranslation } from "react-i18next"
import type { Recommendation } from "@/entities/recommendation/model"
import { useShortlist } from "@/entities/shortlist/store"
import { useMediaQuery } from "@/shared/media/use-media-query"
import { EmptyState } from "@/shared/ui/empty-state"
import { SegmentedControl } from "@/shared/ui/segmented-control"
import { CompanyList } from "../company-list"
import { CompareDialog } from "../compare-dialog"
import { EvidencePanel } from "../evidence-panel"
import { ProductList } from "../product-list"
import { ProfilePanel } from "../profile-panel"
import styles from "./styles.module.css"

export const NARROW_LAYOUT = "(max-width: 47.99rem)"
const VIEWS = ["products", "companies", "evidence"] as const
type View = (typeof VIEWS)[number]

export type WorkspaceProps = {
  readonly uploadId: string
  readonly lotId: string
  readonly recommendation: Recommendation
}

export function Workspace({ uploadId, lotId, recommendation }: WorkspaceProps) {
  const { t } = useTranslation("lot")
  const { products, companies } = recommendation
  const narrow = useMediaQuery(NARROW_LAYOUT)
  const shortlist = useShortlist(uploadId, lotId)
  const [view, setView] = useState<View>("evidence")
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
    if (narrow) setView("evidence")
  }

  function filter(productId: string | null) {
    setFilterId(productId)
    if (narrow && productId) setView("companies")
  }

  const productPane = <ProductList products={products} filterId={filterId} onFilter={filter} />
  if (!selected) {
    return (
      <div className={styles.empty}>
        {productPane}
        <EmptyState
          headingLevel={2}
          title={t("noCandidates.title")}
          description={t("noCandidates.text")}
        />
      </div>
    )
  }

  const companyPane = (
    <CompanyList
      companies={shown}
      ranks={ranks}
      products={products}
      selectedId={selected.id}
      chosen={shortlist.ids}
      filter={
        filterProduct ? { name: filterProduct.name, onReset: () => filter(null) } : undefined
      }
      onSelect={select}
      onCompare={() => setCompareOpen(true)}
    />
  )
  const evidencePane = (
    <EvidencePanel
      key={selected.id}
      company={selected}
      products={products}
      chosen={shortlist.ids.includes(selected.id)}
      onChoose={() => shortlist.toggle(selected.id)}
      onProfile={() => setProfileOpen(true)}
    />
  )
  const panes: Record<View, ReactElement> = {
    products: productPane,
    companies: companyPane,
    evidence: evidencePane,
  }

  return (
    <>
      {narrow ? (
        <div className={styles.stacked}>
          <SegmentedControl
            legend={t("views.legend")}
            value={view}
            onChange={setView}
            options={VIEWS.map((value) => ({ value, label: t(`views.${value}`) }))}
          />
          {panes[view]}
        </div>
      ) : (
        <div className={styles.columns}>
          <div className={clsx(styles.pane, styles.products)}>{productPane}</div>
          <div className={styles.pane}>{companyPane}</div>
          <div className={styles.pane}>{evidencePane}</div>
        </div>
      )}
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
