import { useId, useState } from "react"
import { WarningNote } from "@/entities/evidence/ui/warning-note"
import type { SearchResult } from "@/entities/search/model"
import { candidateView, itemViews } from "@/entities/search/view"
import { useSearchShortlist } from "@/entities/shortlist/store"
import { CompareButton, CompareDialog } from "@/features/compare-candidates"
import { SearchExportDialog } from "@/features/export-results"
import type { SearchStage } from "@/features/search-box"
import { useInView } from "@/shared/media/use-in-view"
import { ResultHeader } from "../result-header"
import { firstShow } from "../reveal"
import { SearchWorkspace } from "../search-workspace"
import styles from "./styles.module.css"

export function ResultView({ result }: { readonly result: SearchResult }) {
  const inputId = useId()
  const shortlist = useSearchShortlist(result.searchId)
  const [reveal] = useState(() => firstShow(result.searchId))
  const [exporting, setExporting] = useState(false)
  const [comparing, setComparing] = useState(false)
  const [stage, setStage] = useState<SearchStage | null>(null)
  const [actionsRef, actionsInView] = useInView<HTMLDivElement>()
  const known = shortlist.ids.filter((id) => result.candidates.some((item) => item.id === id))
  const chosen = result.candidates
    .filter((item) => known.includes(item.id))
    .map((item) => candidateView(item, result.offers))

  return (
    <div className={styles.view}>
      <ResultHeader
        result={result}
        inputId={inputId}
        chosen={known.length}
        stage={stage}
        actionsRef={actionsRef}
        onStage={setStage}
        onExport={() => setExporting(true)}
        onCompare={() => setComparing(true)}
        onClear={() => {
          for (const id of known) shortlist.toggle(id)
        }}
      />
      <div className={styles.body} aria-busy={stage !== null} inert={stage !== null}>
        {result.warnings.length > 0 ? <WarningNote warnings={result.warnings} /> : null}
        <SearchWorkspace
          result={result}
          chosen={known}
          reveal={reveal}
          dockAction={
            actionsInView ? null : (
              <CompareButton
                compact
                count={known.length}
                onCompare={() => setComparing(true)}
              />
            )
          }
          onToggle={shortlist.toggle}
          onEditQuery={() => document.getElementById(inputId)?.focus()}
        />
      </div>
      <SearchExportDialog
        open={exporting}
        onClose={() => setExporting(false)}
        result={result}
        chosen={known}
      />
      <CompareDialog
        open={comparing}
        candidates={chosen}
        items={itemViews(result.items)}
        onClose={() => setComparing(false)}
      />
    </div>
  )
}
