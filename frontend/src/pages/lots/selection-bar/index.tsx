import { useState } from "react"
import { useTranslation } from "react-i18next"
import { usePresence } from "@/shared/motion/use-presence"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { TextButton } from "@/shared/ui/text-button"
import styles from "./styles.module.css"

export type SelectionBarProps = {
  readonly count: number
  readonly onExport: () => void
  readonly onClear: () => void
}

export function SelectionBar({ count, onExport, onClear }: SelectionBarProps) {
  const { t } = useTranslation("lots")
  const open = count > 0
  const { isMounted, state, onAnimationEnd } = usePresence(open)
  const [shown, setShown] = useState(count)
  if (open && count !== shown) setShown(count)
  if (!isMounted) return null
  return (
    <section
      className={styles.bar}
      aria-label={t("selection.label")}
      data-state={state}
      inert={!open}
      onAnimationEnd={onAnimationEnd}
    >
      <span className={styles.count} aria-live="polite">
        {t("selection.count", { count: shown })}
      </span>
      <TextButton className={styles.clear} onClick={onClear}>
        {t("selection.clear")}
      </TextButton>
      <Button variant="strong" className={styles.export} onClick={onExport}>
        <Icon name="download" />
        {t("selection.export")}
      </Button>
    </section>
  )
}
