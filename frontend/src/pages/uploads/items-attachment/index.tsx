import { useId } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/shared/ui/button"
import styles from "./styles.module.css"

type ItemsAttachmentProps = {
  readonly file: File | undefined
  readonly onChange: (file: File | undefined) => void
}

export function ItemsAttachment({ file, onChange }: ItemsAttachmentProps) {
  const { t } = useTranslation("uploads")
  const id = useId()
  return (
    <section className={styles.attachment}>
      <label htmlFor={id}>{t("items.title")}</label>
      <p id={`${id}-hint`}>{t("items.hint")}</p>
      <input
        key={file?.name ?? "empty"}
        id={id}
        type="file"
        accept=".csv,text/csv"
        aria-describedby={`${id}-hint`}
        onChange={(event) => onChange(event.target.files?.[0])}
      />
      {file ? (
        <Button variant="secondary" onClick={() => onChange(undefined)}>
          {t("items.remove")}
        </Button>
      ) : null}
    </section>
  )
}
