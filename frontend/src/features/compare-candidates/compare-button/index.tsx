import { clsx } from "clsx"
import { useId, useState } from "react"
import { useTranslation } from "react-i18next"
import { usePresence } from "@/shared/motion/use-presence"
import { Button } from "@/shared/ui/button"
import { CountBadge } from "@/shared/ui/count-badge"
import { Icon } from "@/shared/ui/icon"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export const COMPARE_FROM = 2

export type CompareButtonProps = {
  readonly count: number
  readonly className?: string
  readonly labelClassName?: string
  readonly onCompare: () => void
}

export function CompareButton({
  count,
  className,
  labelClassName,
  onCompare,
}: CompareButtonProps) {
  const { t } = useTranslation("candidate")
  const hintId = useId()
  const { isMounted, state, onAnimationEnd } = usePresence(count > 0)
  const [shown, setShown] = useState(count)
  if (count > 0 && count !== shown) setShown(count)
  if (!isMounted) return null
  const ready = shown >= COMPARE_FROM
  return (
    <>
      <Button
        variant="secondary"
        className={clsx(styles.button, className)}
        data-state={state}
        inert={count === 0}
        aria-label={t("selection.compareLabel", { count: shown })}
        aria-disabled={!ready || undefined}
        aria-describedby={ready ? undefined : hintId}
        title={ready ? undefined : t("selection.compareHint")}
        onAnimationEnd={onAnimationEnd}
        onClick={() => {
          if (ready) onCompare()
        }}
      >
        <Icon name="compare" />
        <span className={labelClassName}>{t("selection.compare")}</span>
        <CountBadge value={shown} corner />
      </Button>
      {ready ? null : <VisuallyHidden id={hintId}>{t("selection.compareHint")}</VisuallyHidden>}
    </>
  )
}
