import { useState } from "react"
import { useTranslation } from "react-i18next"
import { CandidateList } from "@/entities/evidence/ui/candidate-list"
import { CandidatePanel, offerEntries } from "@/entities/evidence/ui/candidate-panel"
import { coverageOf, rowsOf } from "@/entities/evidence/view"
import type { CandidateStatus, SearchResult } from "@/entities/search/model"
import { candidateView, itemViews } from "@/entities/search/view"
import { SupplierProfilePanel } from "@/entities/supplier/ui/profile-panel"
import { useFormatters } from "@/shared/i18n/formatters"
import { useMediaQuery } from "@/shared/media/use-media-query"
import { useQueryState } from "@/shared/routing/use-query-state"
import { SegmentedControl } from "@/shared/ui/segmented-control"
import {
  parseView,
  useWorkspaceView,
  viewParam,
  WorkspaceLayout,
  type WorkspaceView,
} from "@/shared/ui/workspace-layout"
import { EmptyResult } from "../empty-result"
import { ItemList } from "../item-list"

export const SEARCH_PARAMS = ["candidate", "item", "view", "status"] as const
export const MEDIUM_LAYOUT = "(min-width: 48rem) and (max-width: 74.99rem)"

type Facet = "all" | CandidateStatus
const FACETS: readonly Facet[] = ["all", "recommended", "check"]

function parseFacet(value: string | null): Facet {
  return FACETS.find((facet) => facet === value) ?? "all"
}

export type SearchWorkspaceProps = {
  readonly result: SearchResult
  readonly chosen: readonly string[]
  readonly reveal: boolean
  readonly onToggle: (id: string) => void
  readonly onEditQuery: () => void
}

export function SearchWorkspace({
  result,
  chosen,
  reveal,
  onToggle,
  onEditQuery,
}: SearchWorkspaceProps) {
  const { t } = useTranslation("search")
  const { t: candidateText } = useTranslation("candidate")
  const { number } = useFormatters()
  const [params, update] = useQueryState(SEARCH_PARAMS)
  const view = parseView(params.view)
  const { narrow, stackRef, prepareSwitch } = useWorkspaceView(view)
  const medium = useMediaQuery(MEDIUM_LAYOUT)
  const [profileOpen, setProfileOpen] = useState(false)
  const items = itemViews(result.items)
  const candidates = result.candidates.map((candidate) =>
    candidateView(candidate, result.offers),
  )
  const facet = parseFacet(params.status)
  const focusItem = result.items.find((item) => item.id === params.item)
  const focusId = focusItem?.id ?? null
  const shown = candidates.filter(
    (candidate) =>
      coverageOf(candidate, focusId) && (facet === "all" || candidate.status === facet),
  )
  const selected =
    shown.find((candidate) => candidate.id === params.candidate) ??
    shown[0] ??
    candidates.find((candidate) => candidate.id === params.candidate) ??
    candidates[0]

  if (!selected) {
    return <EmptyResult result={result} onEditQuery={onEditQuery} />
  }

  function show(next: WorkspaceView) {
    prepareSwitch(false)
    update({ view: viewParam(next) })
  }

  function select(id: string) {
    if (narrow) prepareSwitch(true)
    update({ candidate: id, ...(narrow ? { view: viewParam("evidence") } : {}) })
  }

  function filter(next: string | null) {
    const move = narrow && next !== null
    if (move) prepareSwitch(true)
    update({ item: next, ...(move ? { view: viewParam("candidates") } : {}) })
  }

  const position = shown.findIndex((candidate) => candidate.id === selected.id)
  const neighbour = (step: number) => {
    const target = shown[position + step]
    return position >= 0 && target ? () => update({ candidate: target.id }) : undefined
  }
  const count = (value: Facet) =>
    number(
      candidates.filter(
        (candidate) =>
          coverageOf(candidate, focusId) && (value === "all" || candidate.status === value),
      ).length,
    )
  const labels: Record<WorkspaceView, string> = {
    list: t("views.items"),
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
          list: (
            <ItemList
              items={result.items}
              candidates={result.candidates}
              activeId={focusId}
              compact={medium}
              onFilter={filter}
            />
          ),
          candidates: (
            <CandidateList
              title={t("candidates.title")}
              aside={t("candidates.order")}
              candidates={shown}
              items={items}
              selectedId={selected.id}
              chosen={chosen}
              reveal={reveal}
              noMatch={t("candidates.noMatch")}
              filter={
                focusItem
                  ? {
                      itemId: focusItem.id,
                      text: t("candidates.filtered", { name: focusItem.name }),
                      resetLabel: candidateText("list.reset"),
                      onReset: () => filter(null),
                    }
                  : undefined
              }
              toolbar={
                <SegmentedControl
                  scroll
                  legend={t("candidates.facets.legend")}
                  value={facet}
                  onChange={(next) => update({ status: next === "all" ? null : next })}
                  options={FACETS.map((value) => ({
                    value,
                    label: t(`candidates.facets.${value}`),
                    count: count(value),
                  }))}
                />
              }
              onSelect={select}
            />
          ),
          evidence: (
            <CandidatePanel
              candidate={selected}
              items={items}
              chosen={chosen.includes(selected.id)}
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
              onChoose={() => onToggle(selected.id)}
              onProfile={() => setProfileOpen(true)}
            />
          ),
        }}
      />
      <SupplierProfilePanel
        open={profileOpen}
        supplierId={selected.id}
        name={selected.name}
        matched={offerEntries(rowsOf(selected, items))}
        onClose={() => setProfileOpen(false)}
      />
    </>
  )
}
