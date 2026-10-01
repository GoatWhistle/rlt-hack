import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useUploads } from "@/entities/upload/queries"
import { ErrorState } from "@/shared/ui/error-state"
import { LoadingState } from "@/shared/ui/loading-state"
import { Intro } from "./intro"
import styles from "./styles.module.css"
import { UploadDialog } from "./upload-dialog"
import { UploadList } from "./upload-list"

type DialogState = {
  readonly open: boolean
  readonly file: File | null
  readonly session: number
}

export function UploadsPage() {
  const { t } = useTranslation()
  const uploads = useUploads()
  const [dialog, setDialog] = useState<DialogState>({ open: false, file: null, session: 0 })

  function openDialog(file: File | null) {
    setDialog((current) => ({ open: true, file, session: current.session + 1 }))
  }

  if (uploads.isPending) return <LoadingState label={t("state.loading")} />
  if (uploads.isError) {
    return (
      <ErrorState error={uploads.error} headingLevel={1} onRetry={() => uploads.refetch()} />
    )
  }

  return (
    <div className={styles.page}>
      {uploads.data.length === 0 ? (
        <Intro onFile={openDialog} />
      ) : (
        <UploadList uploads={uploads.data} onUpload={() => openDialog(null)} />
      )}
      <UploadDialog
        key={dialog.session}
        open={dialog.open}
        initialFile={dialog.file}
        onClose={() => setDialog((current) => ({ ...current, open: false }))}
      />
    </div>
  )
}
