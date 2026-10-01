import type { ReactNode } from "react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { EXIT_FALLBACK_MS } from "@/shared/motion/use-presence"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"
import { type ToastApi, ToastContext, type ToastInput, type ToastTone } from "./toast-context"
import { type ToastEntry, ToastItem } from "./toast-item"

export const DEFAULT_TOAST_MS = 5000
export const ERROR_TOAST_MS = 10000
export const MAX_TOASTS = 3

type Announcement = { readonly polite: string; readonly assertive: string }

function durationOf(tone: ToastTone, durationMs?: number): number {
  return durationMs ?? (tone === "error" ? ERROR_TOAST_MS : DEFAULT_TOAST_MS)
}

export type ToastProviderProps = {
  readonly children: ReactNode
}

export function ToastProvider({ children }: ToastProviderProps) {
  const { t } = useTranslation()
  const [entries, setEntries] = useState<readonly ToastEntry[]>([])
  const [announcement, setAnnouncement] = useState<Announcement>({ polite: "", assertive: "" })
  const nextId = useRef(0)
  const timers = useRef(new Set<number>())

  const later = useCallback((callback: () => void, delay: number) => {
    const timer = window.setTimeout(() => {
      timers.current.delete(timer)
      callback()
    }, delay)
    timers.current.add(timer)
  }, [])

  const dismiss = useCallback(
    (id: number) => {
      setEntries((current) =>
        current.map((entry) => (entry.id === id ? { ...entry, open: false } : entry)),
      )
      later(
        () => setEntries((current) => current.filter((entry) => entry.id !== id)),
        EXIT_FALLBACK_MS,
      )
    },
    [later],
  )

  const show = useCallback(({ message, tone = "info", durationMs }: ToastInput) => {
    nextId.current += 1
    const id = nextId.current
    const entry = { id, message, tone, open: true, durationMs: durationOf(tone, durationMs) }
    setEntries((current) => [...current, entry].slice(-MAX_TOASTS))
    setAnnouncement((current) =>
      tone === "error" ? { ...current, assertive: message } : { ...current, polite: message },
    )
    return id
  }, [])

  useEffect(() => {
    const pending = timers.current
    return () => {
      for (const timer of pending) window.clearTimeout(timer)
    }
  }, [])

  const api = useMemo<ToastApi>(() => ({ show, dismiss }), [show, dismiss])

  return (
    <ToastContext value={api}>
      {children}
      <section className={styles.viewport} aria-label={t("notifications.label")}>
        <VisuallyHidden aria-live="polite" aria-atomic="true">
          {announcement.polite}
        </VisuallyHidden>
        <VisuallyHidden aria-live="assertive" aria-atomic="true">
          {announcement.assertive}
        </VisuallyHidden>
        <ol className={styles.list}>
          {entries.map((entry) => (
            <ToastItem key={entry.id} entry={entry} onDismiss={dismiss} />
          ))}
        </ol>
      </section>
    </ToastContext>
  )
}
