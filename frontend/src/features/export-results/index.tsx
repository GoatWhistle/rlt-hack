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
import { CSV_TYPE, exportFileNames, productsCsv, suppliersCsv } from "./csv"
import styles from "./styles.module.css"

type LotScope = "lot" | "selected" | "file"
type CandidateScope = "all" | "shortlist"

export type ExportDialogProps = {
  readonly open: boolean
  readonly onClose: () => void
  readonly uploadId: string
  readonly fileName: string
  readonly lots: readonly LotSummary[]
  readonly selectedIds?: readonly string[]
  readonly currentLotId?: string
}

export function ExportDialog(props: ExportDialogProps) {
  const { open, onClose, uploadId, fileName, lots, selectedIds = [], currentLotId } = props
  const { t } = useTranslation("export")
  const gateway = useUploadGateway()
  const initial: LotScope = currentLotId ? "lot" : selectedIds.length > 0 ? "selected" : "file"
  const [lotScope, setLotScope] = useState<LotScope>(initial)
  const [candidates, setCandidates] = useState<CandidateScope>("all")
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)

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
  const ready = inScope.filter((lot) => lot.status !== "queued")
  const pending = inScope.length - ready.length
  const shortlists = shortlistsOf(uploadId)
  const chosen = ready.reduce((sum, lot) => sum + (shortlists[lot.id]?.length ?? 0), 0)

  async function download() {
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
        suppliersCsv(results, candidates === "shortlist" ? shortlists : undefined),
        CSV_TYPE,
      )
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
        <Button disabled={busy || ready.length === 0} onClick={() => void download()}>
          {busy ? t("submitting") : t("submit")}
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
        <RadioGroup
          legend={t("candidates.legend")}
          options={[
            { value: "all", label: t("candidates.all") },
            { value: "shortlist", label: t("candidates.shortlist", { count: chosen }) },
          ]}
          value={candidates}
          onChange={setCandidates}
        />
        <div className={styles.summary} aria-live="polite">
          <p>
            {ready.length > 0 ? t("scope", { count: ready.length }) : t("nothing")}
            {pending > 0 ? ` ${t("pending", { count: pending })}` : ""}
          </p>
          {candidates === "shortlist" && chosen === 0 ? <p>{t("noShortlist")}</p> : null}
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
