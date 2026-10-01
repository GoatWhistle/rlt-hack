import { Icon } from "@/shared/ui/icon"
import { TextButton } from "@/shared/ui/text-button"
import styles from "./styles.module.css"

export type FilterNoteProps = {
  readonly text: string
  readonly resetLabel: string
  readonly onReset: () => void
}

export function FilterNote({ text, resetLabel, onReset }: FilterNoteProps) {
  return (
    <p className={styles.note}>
      <Icon name="filter" size="sm" />
      <span className={styles.text}>{text}</span>
      <TextButton onClick={onReset}>{resetLabel}</TextButton>
    </p>
  )
}
