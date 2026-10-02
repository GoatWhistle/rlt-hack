import { useState } from "react"
import { useTranslation } from "react-i18next"
import { shortlistsOf } from "@/entities/shortlist/store"
import { useUploadGateway } from "@/entities/upload/gateway-context"
import type { LotSummary } from "@/entities/upload/model"
import { saveTextFile } from "@/shared/download/save-text-file"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { Dialog } from "@/shared/ui/dialog"
import { RadioGroup } from "@/shared/ui/radio-group"
import { useToast } from "@/shared/ui/toast/toast-context"
import { type CandidateScope, useCandidateChoice } from "./candidate-choice"
import { CSV_TYPE, exportFileNames, productsCsv, suppliersCsv } from "./csv"
import styles from "./styles.module.css"

export { SearchExportDialog } from "./search-dialog"

type LotScope = "lot" | "selected" | "file"

export type ExportDialogProps = {
  readonly open: boolean
  readonly onClose: () => void
  readonly uploadId: string
  readonly fileName: string
  readonly lots: readonly LotSummary[]
  readonly selectedIds?: readonly string[]
  readonly currentLotId?: string
}

function initialScope(currentLotId: string | undefined, selected: number): LotScope {
  if (currentLotId) return "lot"
  return selected > 0 ? "selected" : "file"
}

export function ExportDialog(props: ExportDialogProps) {
  const { open, onClose, uploadId, fileName, lots, selectedIds = [], currentLotId } = props
  const { t } = useTranslation("export")
  const gateway = useUploadGateway()
  const toast = useToast()
  const [lotScope, setLotScope] = useState<LotScope>(() =>
    initialScope(currentLotId, selectedIds.length),
  )
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const [wasOpen, setWasOpen] = useState(open)

  const scopes: { value: LotScope; label: string; ids: readonly string[] }[] = [
    ...(currentLotId
      ? [{ value: "lot" as const, label: t("lots.lot"), ids: [currentLotId] }]
      : []),
    ...(selectedIds.length > 0
      ? [
          {
            value: "selected" as const,
            label: t("lots.selected", { count: selectedIds.length }),
            ids: selectedIds,
          },
        ]
      : []),
    {
      value: "file",
      label: t("lots.file", { count: lots.length }),
      ids: lots.map((l) => l.id),
    },
  ]
  const ids = new Set(scopes.find((scope) => scope.value === lotScope)?.ids ?? [])
  const inScope = lots.filter((lot) => ids.has(lot.id))
  const ready = inScope.filter((lot) => lot.status !== "queued" && lot.status !== "failed")
  const pending = inScope.filter((lot) => lot.status === "queued").length
  const shortlists = shortlistsOf(uploadId)
  const chosen = ready.reduce((sum, lot) => sum + (shortlists[lot.id]?.length ?? 0), 0)
  const choice = useCandidateChoice(chosen, t("noShortlist"))

  if (open !== wasOpen) {
    setWasOpen(open)
    if (open) {
      setLotScope(initialScope(currentLotId, selectedIds.length))
      setFailed(false)
      choice.reset()
    }
  }

  async function download(scope: CandidateScope) {
    setBusy(true)
    setFailed(false)
    try {
      const results = await gateway.results(
        uploadId,
        ready.map((lot) => lot.id),
      )
      const names = exportFileNames(fileName)
      saveTextFile(names.products, productsCsv(results), CSV_TYPE)
      saveTextFile(
        names.suppliers,
        suppliersCsv(results, scope === "shortlist" ? shortlists : undefined),
        CSV_TYPE,
      )
      toast.show({ tone: "success", message: t("done") })
      onClose()
    } catch {
      setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog
      open={open}
      title={t("title")}
      onClose={onClose}
      footer={
        <Button
          disabled={ready.length === 0}
          pending={busy}
          pendingLabel={t("submitting")}
          onClick={() => void download(choice.scope)}
        >
          {t("submit")}
        </Button>
      }
    >
      <div className={styles.body}>
        <RadioGroup
          legend={t("lots.legend")}
          options={scopes}
          value={lotScope}
          onChange={setLotScope}
        />
        {choice.field}
        <div className={styles.summary} aria-live="polite">
          <p>
            {ready.length > 0 ? t("scope", { count: ready.length }) : t("nothing")}
            {pending > 0 ? ` ${t("pending", { count: pending })}` : ""}
          </p>
          <Caption>{t("files")}</Caption>
        </div>
        {failed ? (
          <p role="alert" className={styles.error}>
            {t("failed")}
          </p>
        ) : null}
      </div>
    </Dialog>
  )
}
