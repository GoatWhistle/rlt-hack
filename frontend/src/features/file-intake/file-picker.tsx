import { type RefObject, useCallback, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { ACCEPTED_FILES, MAX_FILE_MB } from "./model"

export type FilePicker = {
  readonly input: RefObject<HTMLInputElement | null>
  readonly open: () => void
}

export function useFilePicker(): FilePicker {
  const input = useRef<HTMLInputElement>(null)
  const open = useCallback(() => input.current?.click(), [])
  return { input, open }
}

export type FileInputProps = {
  readonly picker: FilePicker
  readonly onFile: (file: File) => void
}

export function FileInput({ picker, onFile }: FileInputProps) {
  return (
    <input
      ref={picker.input}
      type="file"
      accept={ACCEPTED_FILES}
      hidden
      tabIndex={-1}
      aria-hidden="true"
      data-part="file-input"
      onChange={(event) => {
        const file = event.target.files?.[0]
        event.target.value = ""
        if (file) onFile(file)
      }}
    />
  )
}

export type AttachButtonProps = {
  readonly className?: string
  readonly disabled?: boolean
  readonly onClick: () => void
}

export function AttachButton({ className, disabled, onClick }: AttachButtonProps) {
  const { t } = useTranslation("uploads")
  return (
    <Button
      variant="secondary"
      className={className}
      aria-disabled={disabled || undefined}
      onClick={() => {
        if (!disabled) onClick()
      }}
    >
      <Icon name="paperclip" />
      {t("intake.attach")}
    </Button>
  )
}

export function FormatsHint() {
  const { t } = useTranslation("uploads")
  return <>{t("intake.formats", { limit: MAX_FILE_MB })}</>
}
