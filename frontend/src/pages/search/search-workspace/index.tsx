import { useState } from "react"
import { useTranslation } from "react-i18next"
import { matchOf, type SearchResult } from "@/entities/search/model"
import { SupplierProfilePanel } from "@/entities/supplier/ui/profile-panel"
import { searchDraftPath } from "@/shared/config/paths"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import {
  useWorkspaceView,
  WorkspaceEmpty,
  WorkspaceLayout,
  type WorkspaceView,
} from "@/shared/ui/workspace-layout"
import { CandidateList } from "../candidate-list"
import { CandidatePanel } from "../candidate-panel"
import { ItemList } from "../item-list"

export function SearchWorkspace({ result }: { readonly result: SearchResult }) {
  const { t } = useTranslation("search")
  const { items, candidates } = result
  const { narrow, view, show, stackRef } = useWorkspaceView()
  const [selectedId, setSelectedId] = useState(candidates[0]?.id)
  const [itemId, setItemId] = useState<string | null>(null)
  const [profileOpen, setProfileOpen] = useState(false)

  const focusItem = items.find((item) => item.id === itemId)
  const shown = focusItem
    ? candidates.filter((candidate) => matchOf(candidate, focusItem.id))
    : candidates
  const selected =
    shown.find((candidate) => candidate.id === selectedId) ??
    shown[0] ??
    candidates.find((candidate) => candidate.id === selectedId)

  function select(id: string) {
    setSelectedId(id)
    if (narrow) show("evidence")
  }

  function filter(next: string | null) {
    setItemId(next)
    if (narrow && next) show("candidates")
  }

  const itemPane = (
    <ItemList items={items} candidates={candidates} activeId={itemId} onFilter={filter} />
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
              onProfile={() => setProfileOpen(true)}
            />
          ),
        }}
      />
      <SupplierProfilePanel
        open={profileOpen}
        supplierId={selected.id}
        name={selected.name}
        onClose={() => setProfileOpen(false)}
      />
    </>
  )
}
