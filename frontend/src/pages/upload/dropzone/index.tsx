import { clsx } from "clsx"
import { type ChangeEvent, type DragEvent, useState } from "react"
import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export const ACCEPTED_FILES = ".xlsx,.xls"

export type DropzoneProps = {
  readonly onSelect: (file: File) => void
}

export function Dropzone({ onSelect }: DropzoneProps) {
  const { t } = useTranslation()
  const [dragging, setDragging] = useState(false)

  function pick(files: FileList | null) {
    const file = files?.[0]
    if (file) onSelect(file)
  }

  function drop(event: DragEvent<HTMLElement>) {
    event.preventDefault()
    setDragging(false)
    pick(event.dataTransfer.files)
  }

  function dragOver(event: DragEvent<HTMLElement>) {
    event.preventDefault()
    setDragging(true)
  }

  return (
    <section
      aria-label={t("upload.dropTitle")}
      className={clsx(styles.zone, dragging && styles.active)}
      onDragOver={dragOver}
      onDragLeave={() => setDragging(false)}
      onDrop={drop}
    >
      <Icon name="upload" size="lg" />
      <p className={styles.title}>{t("upload.dropTitle")}</p>
      <p className={styles.hint}>{t("upload.dropHint")}</p>
      <label className={styles.picker}>
        {t("upload.chooseFile")}
        <input
          type="file"
          accept={ACCEPTED_FILES}
          className={styles.input}
          onChange={(event: ChangeEvent<HTMLInputElement>) => pick(event.target.files)}
        />
      </label>
    </section>
  )
}
