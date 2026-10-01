import { clsx } from "clsx"
import { type CSSProperties, type KeyboardEvent, type ReactNode, useId } from "react"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export type PickCardProps = {
  readonly title: string
  readonly subtitle: ReactNode
  readonly rank: number
  readonly rankLabel: string
  readonly selected: boolean
  readonly onSelect: () => void
  readonly children: ReactNode
  readonly reveal?: number
  readonly tabIndex?: number
  readonly onKeyDown?: (event: KeyboardEvent<HTMLButtonElement>) => void
}

export function PickCard({
  title,
  subtitle,
  rank,
  rankLabel,
  selected,
  onSelect,
  children,
  reveal,
  tabIndex,
  onKeyDown,
}: PickCardProps) {
  const titleId = useId()
  const subtitleId = useId()
  const detailId = useId()
  const style =
    reveal === undefined ? undefined : ({ "--reveal-index": reveal } as CSSProperties)
  return (
    <button
      type="button"
      aria-pressed={selected}
      aria-labelledby={titleId}
      aria-describedby={`${subtitleId} ${detailId}`}
      className={clsx(styles.card, selected && styles.selected)}
      data-reveal={reveal === undefined ? undefined : ""}
      style={style}
      tabIndex={tabIndex}
      onClick={onSelect}
      onKeyDown={onKeyDown}
    >
      <span className={styles.head}>
        <span className={styles.identity}>
          <span id={titleId} className={styles.title}>
            {title}
          </span>
          <span id={subtitleId} className={styles.subtitle}>
            {subtitle}
          </span>
        </span>
        <span className={styles.rank} aria-hidden="true">
          {String(rank).padStart(2, "0")}
        </span>
      </span>
      <span id={detailId} className={styles.detail}>
        <VisuallyHidden>{rankLabel}</VisuallyHidden>
        {children}
      </span>
    </button>
  )
}
