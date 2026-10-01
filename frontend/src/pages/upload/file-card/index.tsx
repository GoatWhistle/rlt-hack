import { useTranslation } from "react-i18next"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

const BYTES_IN_KB = 1024

export type FileCardProps = {
  readonly file: File
  readonly pending: boolean
  readonly onSubmit: (file: File) => void
}

export function FileCard({ file, pending, onSubmit }: FileCardProps) {
  const { t } = useTranslation()
  const size = Math.max(1, Math.round(file.size / BYTES_IN_KB))
  return (
    <div className={styles.card}>
      <div className={styles.info}>
        <span className={styles.badge}>
          <Icon name="check" tone="confirmed" />
        </span>
        <div className={styles.text}>
          <p className={styles.name}>{file.name}</p>
          <Caption>{t("upload.fileSize", { size })}</Caption>
        </div>
      </div>
      <Button disabled={pending} onClick={() => onSubmit(file)}>
        {pending ? t("upload.submitting") : t("upload.submit")}
      </Button>
    </div>
  )
}
