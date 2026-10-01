import { useId, useState } from "react"
import { useTranslation } from "react-i18next"
import { WarningNote } from "@/entities/evidence/ui/warning-note"
import type { SearchResult } from "@/entities/search/model"
import { candidateView, itemViews } from "@/entities/search/view"
import { useSearchShortlist } from "@/entities/shortlist/store"
import { CompareDialog } from "@/features/compare-candidates"
import { SearchExportDialog } from "@/features/export-results"
import { Button } from "@/shared/ui/button"
import { DockArea } from "@/shared/ui/dock-area"
import { Icon } from "@/shared/ui/icon"
import { SelectionBar } from "@/shared/ui/selection-bar"
import { ResultHeader } from "../result-header"
import { firstShow } from "../reveal"
import { SearchWorkspace } from "../search-workspace"

export const COMPARE_FROM = 2

export function ResultView({ result }: { readonly result: SearchResult }) {
  const { t } = useTranslation("candidate")
  const inputId = useId()
  const shortlist = useSearchShortlist(result.searchId)
  const [reveal] = useState(() => firstShow(result.searchId))
  const [exporting, setExporting] = useState(false)
  const [comparing, setComparing] = useState(false)
  const known = shortlist.ids.filter((id) => result.candidates.some((item) => item.id === id))
  const chosen = result.candidates.filter((item) => known.includes(item.id)).map(candidateView)

  return (
    <DockArea docked={known.length > 0}>
      <ResultHeader
        result={result}
        inputId={inputId}
        chosen={known.length}
        onExport={() => setExporting(true)}
      />
      {result.warnings.length > 0 ? <WarningNote warnings={result.warnings} /> : null}
      <SearchWorkspace
        result={result}
        chosen={known}
        reveal={reveal}
        onToggle={shortlist.toggle}
        onEditQuery={() => document.getElementById(inputId)?.focus()}
      />
      <SelectionBar
        count={known.length}
        label={t("selection.label")}
        countText={(count) => t("selection.count", { count })}
        clearLabel={t("selection.clear")}
        onClear={() => {
          for (const id of known) shortlist.toggle(id)
        }}
      >
        <Button
          variant="secondary"
          aria-disabled={known.length < COMPARE_FROM || undefined}
          title={known.length < COMPARE_FROM ? t("selection.compareHint") : undefined}
          onClick={() => {
            if (known.length >= COMPARE_FROM) setComparing(true)
          }}
        >
          <Icon name="compare" />
          {t("selection.compare")}
        </Button>
        <Button variant="strong" onClick={() => setExporting(true)}>
          <Icon name="download" />
          {t("selection.exportShort")}
        </Button>
      </SelectionBar>
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
    </DockArea>
  )
}
