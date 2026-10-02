import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type Choice = {
  readonly chosen: boolean
  readonly onToggle: () => void
}

export type ChoiceButtonProps = Choice & {
  readonly chooseLabel: string
  readonly chosenLabel: string
}

export function ChoiceButton({
  chosen,
  chooseLabel,
  chosenLabel,
  onToggle,
}: ChoiceButtonProps) {
  return (
    <Button variant={chosen ? "secondary" : "primary"} onClick={onToggle}>
      {chosen ? (
        <span className={styles.icon}>
          <Icon name="check" />
        </span>
      ) : null}
      {chosen ? chosenLabel : chooseLabel}
    </Button>
  )
}
