import { clsx } from "clsx"
import { type FocusEvent, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { usePresence } from "@/shared/motion/use-presence"
import styles from "./styles.module.css"
import type { ToastAction, ToastTone } from "./toast-context"

export type ToastEntry = {
  readonly id: number
  readonly message: string
  readonly tone: ToastTone
  readonly open: boolean
  readonly durationMs: number
  readonly action?: ToastAction
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

function useDismissTimer(entry: ToastEntry, paused: boolean, onDismiss: (id: number) => void) {
  const remaining = useRef(entry.durationMs)
  useEffect(() => {
    if (!entry.open || paused) return
    const started = Date.now()
    const timer = window.setTimeout(() => onDismiss(entry.id), remaining.current)
    return () => {
      window.clearTimeout(timer)
      remaining.current = Math.max(0, remaining.current - (Date.now() - started))
    }
  }, [entry.open, entry.id, paused, onDismiss])
}

export function ToastItem({ entry, onDismiss }: ToastItemProps) {
  const { t } = useTranslation()
  const { isMounted, state, onAnimationEnd } = usePresence(entry.open)
  const [hovered, setHovered] = useState(false)
  const [focused, setFocused] = useState(false)
  useDismissTimer(entry, hovered || focused, onDismiss)
  if (!isMounted) return null
  const blur = (event: FocusEvent<HTMLLIElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false)
  }
  return (
    <li
      className={styles.item}
      data-state={state}
      data-tone={entry.tone}
      onAnimationEnd={onAnimationEnd}
      onPointerEnter={() => setHovered(true)}
      onPointerLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={blur}
    >
      <div className={styles.clip}>
        <div className={clsx(styles.toast, TONES[entry.tone])}>
          <p className={styles.message}>{entry.message}</p>
          {entry.action ? (
            <button
              type="button"
              className={styles.action}
              onClick={() => {
                entry.action?.run()
                onDismiss(entry.id)
              }}
            >
              {entry.action.label}
            </button>
          ) : null}
          <button
            type="button"
            className={styles.close}
            aria-label={t("action.dismiss")}
            onClick={() => onDismiss(entry.id)}
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>
      </div>
    </li>
  )
}
