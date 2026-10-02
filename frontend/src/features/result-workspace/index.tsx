import { useState } from "react"
import { useTranslation } from "react-i18next"
import { matchOf, type SearchResult } from "@/entities/search/model"
import { CoverageMatrix } from "@/entities/search/ui/coverage-matrix"
import { useSearchShortlist } from "@/entities/shortlist/store"
import { SupplierProfilePanel } from "@/entities/supplier/ui/profile-panel"
import { searchDraftPath } from "@/shared/config/paths"
import { useQueryState } from "@/shared/routing/use-query-state"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { TextButton } from "@/shared/ui/text-button"
import {
  parseView,
  useWorkspaceView,
  viewParam,
  WorkspaceEmpty,
  WorkspaceLayout,
  type WorkspaceView,
} from "@/shared/ui/workspace-layout"
import { CandidateList } from "./candidate-list"
import { CandidatePanel } from "./candidate-panel"
import { ItemList } from "./item-list"

export const SEARCH_PARAMS = ["candidate", "item", "view"] as const

export function SearchWorkspace({ result }: { readonly result: SearchResult }) {
  const { t } = useTranslation("search")
  const { items, candidates } = result
  const [params, update] = useQueryState(SEARCH_PARAMS)
  const view = parseView(params.view)
  const { narrow, stackRef, prepareSwitch } = useWorkspaceView(view)
  const shortlist = useSearchShortlist(result.searchId)
  const [profileOpen, setProfileOpen] = useState(false)
  const [coverageOpen, setCoverageOpen] = useState(false)

  const focusItem = items.find((item) => item.id === params.item)
  const shown = focusItem
    ? candidates.filter((candidate) => matchOf(candidate, focusItem.id))
    : candidates
  const selected =
    shown.find((candidate) => candidate.id === params.candidate) ??
    shown[0] ??
    candidates.find((candidate) => candidate.id === params.candidate) ??
    candidates[0]

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

  const itemPane = (
    <ItemList
      items={items}
      candidates={candidates}
      activeId={focusItem?.id ?? null}
      onFilter={filter}
    />
  )
  if (!selected) {
    return (
      <WorkspaceEmpty list={items.length > 0 ? itemPane : null}>
        <EmptyState
          icon="search"
          headingLevel={2}
          title={t("empty.title")}
          description={t("empty.text")}
          actions={
            <ButtonLink to={searchDraftPath(result.query.text)}>{t("empty.action")}</ButtonLink>
          }
        />
      </WorkspaceEmpty>
    )
  }

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
          list: itemPane,
          candidates: (
            <CandidateList
              candidates={shown}
              selectedId={selected.id}
              chosen={shortlist.ids}
              filter={
                focusItem ? { name: focusItem.name, onReset: () => filter(null) } : undefined
              }
              onSelect={select}
            />
          ),
          evidence: (
            <CandidatePanel
              key={selected.id}
              candidate={selected}
              items={items}
              noveltySet={result.pipeline.noveltySet}
              chosen={shortlist.ids.includes(selected.id)}
              onChoose={() => shortlist.toggle(selected.id)}
              onProfile={() => setProfileOpen(true)}
            />
          ),
        }}
      />
      <TextButton aria-expanded={coverageOpen} onClick={() => setCoverageOpen(!coverageOpen)}>
        {coverageOpen ? t("coverage.hide") : t("coverage.show")}
      </TextButton>
      {coverageOpen ? (
        <CoverageMatrix candidates={candidates} items={items} onPick={select} />
      ) : null}
      <SupplierProfilePanel
        open={profileOpen}
        supplierId={selected.id}
        name={selected.name || selected.inn}
        onClose={() => setProfileOpen(false)}
      />
    </>
  )
}
