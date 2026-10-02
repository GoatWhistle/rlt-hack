import { useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"
import { isProcessing, type UploadSummary } from "@/entities/upload/model"
import { useToast } from "@/shared/ui/toast/toast-context"

export function useFinishToast(uploads: readonly UploadSummary[] | undefined) {
  const { t } = useTranslation("uploads")
  const toast = useToast()
  const running = useRef<ReadonlySet<string> | null>(null)

  useEffect(() => {
    if (!uploads) return
    const before = running.current
    running.current = new Set(uploads.filter(isProcessing).map((upload) => upload.id))
    if (!before) return
    for (const upload of uploads) {
      if (!before.has(upload.id) || isProcessing(upload)) continue
      toast.show({
        tone: "success",
        message: t("list.finished", {
          file: upload.fileName,
          ready: upload.counts.ready,
          check: upload.counts.needsCheck,
        }),
      })
    }
  }, [uploads, toast, t])
}
