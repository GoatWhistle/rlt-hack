import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router"
import { checkNotices } from "@/entities/notice/check"
import { decodeFile } from "@/entities/notice/decode"
import type { CheckedFile, FileCheck } from "@/entities/notice/model"
import { isProcessing, type UploadSummary } from "@/entities/upload/model"
import { useCreateUpload } from "@/entities/upload/queries"
import { uploadPath } from "@/shared/config/paths"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { Button } from "@/shared/ui/button"
import { Dialog } from "@/shared/ui/dialog"
import { Icon } from "@/shared/ui/icon"
import { StepTrail } from "@/shared/ui/step-trail"
import { useToast } from "@/shared/ui/toast/toast-context"
import { CheckSkeleton, CheckSummary } from "../check-summary"
import { Dropzone } from "../dropzone"
import { ItemsAttachment } from "../items-attachment"
import { ProcessingView } from "../processing-view"
import styles from "./styles.module.css"

type Phase =
  | { readonly kind: "file" }
  | { readonly kind: "reading" }
  | { readonly kind: "checked"; readonly file: File; readonly check: FileCheck }

export async function inspectFile(file: File): Promise<FileCheck> {
  try {
    return checkNotices(await decodeFile(file), file.name)
  } catch {
    return { ok: false, fileName: file.name, problem: "unreadable", missing: [] }
  }
}

type DialogActionsProps = {
  readonly check: FileCheck
  readonly pending: boolean
  readonly onOther: () => void
  readonly onStart: () => void
}

function DialogActions({ check, pending, onOther, onStart }: DialogActionsProps) {
  const { t } = useTranslation("uploads")
  const count = check.ok ? check.notices.length : 0
  return (
    <>
      <Button variant="secondary" disabled={pending} onClick={onOther}>
        {t("dialog.otherFile")}
      </Button>
      {count > 0 ? (
        <Button pending={pending} pendingLabel={t("dialog.starting")} onClick={onStart}>
          {t("dialog.start", { count })}
        </Button>
      ) : null}
    </>
  )
}

function useWatching(open: boolean) {
  const watching = useRef(open)
  useEffect(() => {
    watching.current = open
    return () => {
      watching.current = false
    }
  }, [open])
  return watching
}

function useFinish(open: boolean) {
  const { t } = useTranslation("uploads")
  const navigate = useNavigate()
  const toast = useToast()
  const watching = useWatching(open)
  return (upload: UploadSummary) => {
    const target = uploadPath(upload.id)
    if (watching.current) {
      navigate(target)
      return
    }
    toast.show({
      tone: "success",
      message: isProcessing(upload)
        ? t("dialog.accepted", { file: upload.fileName })
        : t("list.finished", {
            file: upload.fileName,
            ready: upload.counts.ready,
            check: upload.counts.needsCheck,
          }),
      action: { label: t("dialog.open"), run: () => navigate(target) },
    })
  }
}

type UploadBodyProps = {
  readonly phase: Phase
  readonly processing: CheckedFile | null
  readonly onSelect: (file: File) => void
}

function UploadBody({ phase, processing, onSelect }: UploadBodyProps) {
  const { t } = useTranslation("uploads")
  return (
    <div key={processing ? "processing" : phase.kind} className={styles.body}>
      {phase.kind === "file" ? <Dropzone onSelect={onSelect} /> : null}
      {phase.kind === "reading" ? <CheckSkeleton label={t("dialog.reading")} /> : null}
      {processing ? (
        <ProcessingView fileName={processing.fileName} count={processing.notices.length} />
      ) : null}
      {phase.kind === "checked" && !processing ? <CheckSummary check={phase.check} /> : null}
    </div>
  )
}

export type UploadDialogProps = {
  readonly open: boolean
  readonly initialFile: File | null
  readonly onClose: () => void
}

export function UploadDialog({ open, initialFile, onClose }: UploadDialogProps) {
  const { t } = useTranslation("uploads")
  const create = useCreateUpload(useFinish(open))
  const errorMessage = useErrorMessage()
  const [itemsFile, setItemsFile] = useState<File | undefined>()
  const [phase, setPhase] = useState<Phase>(
    initialFile ? { kind: "reading" } : { kind: "file" },
  )

  useEffect(() => {
    if (!initialFile) return
    let active = true
    void inspectFile(initialFile).then((check) => {
      if (active) setPhase({ kind: "checked", file: initialFile, check })
    })
    return () => {
      active = false
    }
  }, [initialFile])

  async function read(file: File) {
    setPhase({ kind: "reading" })
    setPhase({ kind: "checked", file, check: await inspectFile(file) })
  }

  function start(file: File, check: FileCheck) {
    if (!check.ok) return
    create.mutate({ file, check, itemsFile })
  }

  const checked = phase.kind === "checked" ? phase : null
  const accepted = checked?.check.ok ? checked.check : null
  const processing = create.isPending ? accepted : null
  const steps = [t("dialog.steps.file"), t("dialog.steps.check"), t("dialog.steps.processing")]

  return (
    <Dialog
      open={open}
      size="wide"
      title={t("dialog.title")}
      onClose={onClose}
      status={
        checked && create.isError ? (
          <p role="alert" className={styles.error}>
            <Icon name="warning" size="sm" tone="warning" />
            {errorMessage(create.error)}
          </p>
        ) : null
      }
      footer={
        checked ? (
          <DialogActions
            check={checked.check}
            pending={create.isPending}
            onOther={() => {
              create.reset()
              setItemsFile(undefined)
              setPhase({ kind: "file" })
            }}
            onStart={() => start(checked.file, checked.check)}
          />
        ) : null
      }
    >
      <StepTrail
        label={t("dialog.steps.label")}
        steps={steps}
        current={create.isPending ? 2 : checked ? 1 : 0}
      />
      {accepted && !processing ? (
        <ItemsAttachment file={itemsFile} onChange={setItemsFile} />
      ) : null}
      <UploadBody phase={phase} processing={processing} onSelect={(file) => void read(file)} />
    </Dialog>
  )
}
