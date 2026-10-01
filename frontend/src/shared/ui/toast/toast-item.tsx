import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import { usePresence } from "@/shared/motion/use-presence"
import styles from "./styles.module.css"
import type { ToastTone } from "./toast-context"

export type ToastEntry = {
  readonly id: number
  readonly message: string
  readonly tone: ToastTone
  readonly open: boolean
}

const TONES: Record<ToastTone, string | undefined> = {
  info: styles.info,
  success: styles.success,
  error: styles.error,
}

export type ToastItemProps = {
  readonly entry: ToastEntry
  readonly onDismiss: (id: number) => void
}

export function ToastItem({ entry, onDismiss }: ToastItemProps) {
  const { t } = useTranslation()
  const { isMounted, state, onAnimationEnd } = usePresence(entry.open)
  if (!isMounted) return null
  return (
    <li
      className={clsx(styles.toast, TONES[entry.tone])}
      data-state={state}
      role={entry.tone === "error" ? "alert" : "status"}
      onAnimationEnd={onAnimationEnd}
    >
      <p className={styles.message}>{entry.message}</p>
      <button
        type="button"
        className={styles.close}
        aria-label={t("action.dismiss")}
        onClick={() => onDismiss(entry.id)}
      >
        <span aria-hidden="true">×</span>
      </button>
    </li>
  )
}
