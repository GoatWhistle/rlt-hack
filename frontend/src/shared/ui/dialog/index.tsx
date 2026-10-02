import { clsx } from "clsx"
import type { ReactNode, SyntheticEvent } from "react"
import { useEffect, useId, useRef } from "react"
import { useTranslation } from "react-i18next"
import { usePresence } from "@/shared/motion/use-presence"
import { Button } from "@/shared/ui/button"
import styles from "./styles.module.css"

export type DialogProps = {
  readonly open: boolean
  readonly title: string
  readonly onClose: () => void
  readonly children?: ReactNode
  readonly footer?: ReactNode
  readonly status?: ReactNode
  readonly size?: DialogSize
  readonly fit?: boolean
}

export type DialogSize = "default" | "wide" | "side"

const SIZES: Record<DialogSize, string | undefined> = {
  default: undefined,
  wide: styles.wide,
  side: styles.side,
}

export function Dialog({
  open,
  title,
  onClose,
  children,
  footer,
  status,
  size = "default",
  fit = false,
}: DialogProps) {
  const { t } = useTranslation()
  const titleId = useId()
  const ref = useRef<HTMLDialogElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const { isMounted, state, onAnimationEnd } = usePresence(open)

  const trigger = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!isMounted) return
    const active = document.activeElement
    if (active instanceof HTMLElement && !ref.current?.contains(active))
      trigger.current = active
    return () => {
      const target = trigger.current
      if (target?.isConnected) target.focus()
    }
  }, [isMounted])

  useEffect(() => {
    const dialog = ref.current
    if (!isMounted || !dialog) return
    if (!dialog.open) {
      dialog.showModal()
      titleRef.current?.focus()
    }
    const closeOnBackdrop = (event: MouseEvent) => {
      if (event.target === dialog) onClose()
    }
    dialog.addEventListener("click", closeOnBackdrop)
    return () => dialog.removeEventListener("click", closeOnBackdrop)
  }, [isMounted, onClose])

  if (!isMounted) return null

  const cancel = (event: SyntheticEvent<HTMLDialogElement>) => {
    event.preventDefault()
    onClose()
  }

  return (
    <dialog
      ref={ref}
      className={clsx(styles.dialog, SIZES[size])}
      data-state={state}
      aria-labelledby={titleId}
      onCancel={cancel}
      onAnimationEnd={onAnimationEnd}
    >
      <div className={styles.panel}>
        <h2 ref={titleRef} id={titleId} tabIndex={-1} className={styles.title}>
          {title}
        </h2>
        <div className={clsx(styles.body, fit && styles.fit)}>{children}</div>
        <div className={styles.bottom}>
          {status}
          <div className={styles.footer}>
            <Button variant="secondary" onClick={onClose}>
              {t("action.close")}
            </Button>
            {footer}
          </div>
        </div>
      </div>
    </dialog>
  )
}
