import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type AttachButtonProps = {
  readonly attached?: boolean
  readonly onClick: () => void
}

export function AttachButton({ attached = false, onClick }: AttachButtonProps) {
  const { t } = useTranslation("uploads")
  return (
    <button
      type="button"
      className={styles.attach}
      aria-label={t("intake.attach")}
      title={t("intake.attach")}
      data-attached={attached || undefined}
      onClick={onClick}
    >
      <Icon name="paperclip" />
      <span className={styles.text}>{t("intake.attachShort")}</span>
    </button>
  )
}
