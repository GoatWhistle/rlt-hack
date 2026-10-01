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
}

export function Dialog({ open, title, onClose, children, footer }: DialogProps) {
  const { t } = useTranslation()
  const titleId = useId()
  const ref = useRef<HTMLDialogElement>(null)
  const { isMounted, state, onAnimationEnd } = usePresence(open)

  useEffect(() => {
    const dialog = ref.current
    if (!isMounted || !dialog) return
    if (!dialog.open) dialog.showModal()
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
      className={styles.dialog}
      data-state={state}
      aria-labelledby={titleId}
      onCancel={cancel}
      onAnimationEnd={onAnimationEnd}
    >
      <div className={styles.panel}>
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        {children}
        <div className={styles.footer}>
          {footer}
          <Button variant="secondary" onClick={onClose}>
            {t("action.close")}
          </Button>
        </div>
      </div>
    </dialog>
  )
}
