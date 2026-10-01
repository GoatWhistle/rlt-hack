import { clsx } from "clsx"
import { type ChangeEvent, type DragEvent, useState } from "react"
import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export const ACCEPTED_FILES = ".csv,text/csv"

export type DropzoneProps = {
  readonly onSelect: (file: File) => void
}

export function Dropzone({ onSelect }: DropzoneProps) {
  const { t } = useTranslation("uploads")
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
      aria-label={t("drop.title")}
      className={clsx(styles.zone, dragging && styles.active)}
      onDragOver={dragOver}
      onDragLeave={() => setDragging(false)}
      onDrop={drop}
    >
      <span className={styles.tile}>
        <Icon name="upload" size="lg" tone="source" />
      </span>
      <p className={styles.title}>{t("drop.title")}</p>
      <p className={styles.hint}>{t("drop.hint")}</p>
      <label className={styles.picker}>
        {t("drop.choose")}
        <input
          type="file"
          accept={ACCEPTED_FILES}
          className={styles.input}
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            pick(event.target.files)
            event.target.value = ""
          }}
        />
      </label>
    </section>
  )
}
