import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useCheckReasonText, useHighlightText } from "@/entities/evidence/labels"
import type { SearchResult } from "@/entities/search/model"
import { saveTextFile } from "@/shared/download/save-text-file"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { Dialog } from "@/shared/ui/dialog"
import { useToast } from "@/shared/ui/toast/toast-context"
import { useCandidateChoice } from "./candidate-choice"
import { CSV_TYPE } from "./csv"
import { searchCsv, searchFileName } from "./search-csv"
import styles from "./styles.module.css"

export type SearchExportDialogProps = {
  readonly open: boolean
  readonly onClose: () => void
  readonly result: SearchResult
  readonly chosen: readonly string[]
}

export function SearchExportDialog({ open, onClose, result, chosen }: SearchExportDialogProps) {
  const { t } = useTranslation("export")
  const toast = useToast()
  const labels = { checkReason: useCheckReasonText(), highlight: useHighlightText() }
  const known = chosen.filter((id) => result.candidates.some((item) => item.id === id))
  const choice = useCandidateChoice(known.length, t("search.noShortlist"))
  const [wasOpen, setWasOpen] = useState(open)
  if (open !== wasOpen) {
    setWasOpen(open)
    if (open) choice.reset()
  }
  const count = choice.scope === "shortlist" ? known.length : result.candidates.length

  function download() {
    const name = searchFileName(result.searchId)
    const kept = choice.scope === "shortlist" ? known : undefined
    saveTextFile(name, searchCsv(result, labels, kept), CSV_TYPE)
    toast.show({ tone: "success", message: t("search.done", { name }) })
    onClose()
  }

  return (
    <Dialog
      open={open}
      title={t("search.title")}
      onClose={onClose}
      footer={<Button onClick={download}>{t("search.submit")}</Button>}
    >
      <div className={styles.body}>
        {choice.field}
        <div className={styles.summary} aria-live="polite">
          <p>{t("search.scope", { count })}</p>
          <Caption>{t("search.files")}</Caption>
        </div>
      </div>
    </Dialog>
  )
}
