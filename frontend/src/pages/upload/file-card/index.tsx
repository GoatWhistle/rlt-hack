import { useTranslation } from "react-i18next"
import { Caption } from "@/shared/ui/caption"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

const BYTES_IN_KB = 1024

export type FileCardProps = {
  readonly file: File
  readonly onClear: () => void
}

export function FileCard({ file, onClear }: FileCardProps) {
  const { t } = useTranslation()
  const size = Math.max(1, Math.round(file.size / BYTES_IN_KB))
  return (
    <div className={styles.card}>
      <span className={styles.badge}>
        <Icon name="fileCheck" tone="confirmed" />
      </span>
      <div className={styles.text}>
        <p className={styles.name}>{file.name}</p>
        <Caption>{t("upload.fileSize", { size })}</Caption>
      </div>
      <button
        type="button"
        className={styles.clear}
        aria-label={t("upload.removeFile")}
        onClick={onClear}
      >
        <Icon name="close" />
      </button>
    </div>
  )
}
