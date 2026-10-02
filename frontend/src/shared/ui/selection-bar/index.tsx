import { type ReactNode, useState } from "react"
import { usePresence } from "@/shared/motion/use-presence"
import { TextButton } from "@/shared/ui/text-button"
import styles from "./styles.module.css"

export type SelectionBarProps = {
  readonly count: number
  readonly label: string
  readonly countText: (count: number) => string
  readonly clearLabel: string
  readonly onClear: () => void
  readonly children: ReactNode
}

export function SelectionBar({
  count,
  label,
  countText,
  clearLabel,
  onClear,
  children,
}: SelectionBarProps) {
  const open = count > 0
  const { isMounted, state, onAnimationEnd } = usePresence(open)
  const [shown, setShown] = useState(count)
  if (open && count !== shown) setShown(count)
  if (!isMounted) return null
  return (
    <section
      className={styles.bar}
      aria-label={label}
      data-state={state}
      data-dock=""
      inert={!open}
      onAnimationEnd={onAnimationEnd}
    >
      <span className={styles.count} aria-live="polite">
        <span key={shown} className={styles.number}>
          {countText(shown)}
        </span>
      </span>
      <TextButton className={styles.clear} onClick={onClear}>
        {clearLabel}
      </TextButton>
      <span className={styles.actions}>{children}</span>
    </section>
  )
}
