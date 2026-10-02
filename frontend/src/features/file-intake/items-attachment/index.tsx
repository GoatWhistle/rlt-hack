import { useId, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { TextButton } from "@/shared/ui/text-button"
import { sizeOf } from "../model"
import styles from "./styles.module.css"

export type ItemsAttachmentProps = {
  readonly file: File | undefined
  readonly onChange: (file: File | undefined) => void
}

export function ItemsAttachment({ file, onChange }: ItemsAttachmentProps) {
  const { t } = useTranslation("uploads")
  const id = useId()
  const input = useRef<HTMLInputElement>(null)
  const size = file ? sizeOf(file.size) : null
  return (
    <section className={styles.items} aria-labelledby={`${id}-title`}>
      <div className={styles.text}>
        <h2 id={`${id}-title`} className={styles.title}>
          {t("items.title")}
        </h2>
        <p id={`${id}-hint`} className={styles.hint}>
          {t("items.hint")}
        </p>
      </div>
      <input
        ref={input}
        id={id}
        key={file?.name ?? "empty"}
        type="file"
        accept=".csv,text/csv"
        className={styles.input}
        aria-label={t("items.title")}
        aria-describedby={`${id}-hint`}
        onChange={(event) => onChange(event.target.files?.[0])}
      />
      {file && size ? (
        <span className={styles.file}>
          <Icon name="file" />
          <span className={styles.name}>{file.name}</span>
          <span className={styles.size}>
            {t(`intake.size.${size.unit}`, { size: size.value })}
          </span>
          <TextButton onClick={() => onChange(undefined)}>{t("items.remove")}</TextButton>
        </span>
      ) : (
        <Button variant="secondary" onClick={() => input.current?.click()}>
          <Icon name="paperclip" />
          {t("items.add")}
        </Button>
      )}
    </section>
  )
}
