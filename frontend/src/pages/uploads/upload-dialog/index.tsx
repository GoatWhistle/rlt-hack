import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router"
import { checkNotices } from "@/entities/notice/check"
import { decodeFile } from "@/entities/notice/decode"
import type { FileCheck } from "@/entities/notice/model"
import { useUploadGateway } from "@/entities/upload/gateway-context"
import { useCreateUpload } from "@/entities/upload/queries"
import { uploadPath } from "@/shared/config/paths"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { Button } from "@/shared/ui/button"
import { Dialog } from "@/shared/ui/dialog"
import { Icon } from "@/shared/ui/icon"
import { StepTrail } from "@/shared/ui/step-trail"
import { CheckSkeleton, CheckSummary } from "../check-summary"
import { Dropzone } from "../dropzone"
import styles from "./styles.module.css"

type Phase =
  | { readonly kind: "file" }
  | { readonly kind: "reading" }
  | { readonly kind: "checked"; readonly file: File; readonly check: FileCheck }

export async function inspectFile(file: File, maxRows: number): Promise<FileCheck> {
  try {
    return checkNotices(await decodeFile(file), file.name, { maxRows })
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
      <Button variant="secondary" onClick={onOther}>
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

export type UploadDialogProps = {
  readonly open: boolean
  readonly initialFile: File | null
  readonly onClose: () => void
}

export function UploadDialog({ open, initialFile, onClose }: UploadDialogProps) {
  const { t } = useTranslation("uploads")
  const navigate = useNavigate()
  const gateway = useUploadGateway()
  const create = useCreateUpload()
  const errorMessage = useErrorMessage()
  const [phase, setPhase] = useState<Phase>(
    initialFile ? { kind: "reading" } : { kind: "file" },
  )

  useEffect(() => {
    if (!initialFile) return
    let active = true
    void inspectFile(initialFile, gateway.maxNotices).then((check) => {
      if (active) setPhase({ kind: "checked", file: initialFile, check })
    })
    return () => {
      active = false
    }
  }, [initialFile, gateway.maxNotices])

  async function read(file: File) {
    setPhase({ kind: "reading" })
    setPhase({ kind: "checked", file, check: await inspectFile(file, gateway.maxNotices) })
  }

  function start(file: File, check: FileCheck) {
    if (!check.ok) return
    create.mutate(
      { file, check },
      { onSuccess: (upload) => navigate(uploadPath(upload.id)) },
    )
  }

  const checked = phase.kind === "checked" ? phase : null
  const steps = [t("dialog.steps.file"), t("dialog.steps.check"), t("dialog.steps.processing")]

  return (
    <Dialog
      open={open}
      size="wide"
      title={t("dialog.title")}
      onClose={onClose}
      footer={
        checked ? (
          <DialogActions
            check={checked.check}
            pending={create.isPending}
            onOther={() => {
              create.reset()
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
      <div key={phase.kind} className={styles.body}>
        {phase.kind === "file" ? <Dropzone onSelect={(file) => void read(file)} /> : null}
        {phase.kind === "reading" ? <CheckSkeleton label={t("dialog.reading")} /> : null}
        {checked ? <CheckSummary check={checked.check} /> : null}
        {checked && create.isError ? (
          <p role="alert" className={styles.error}>
            <Icon name="warning" size="sm" tone="warning" />
            {errorMessage(create.error)}
          </p>
        ) : null}
      </div>
    </Dialog>
  )
}
