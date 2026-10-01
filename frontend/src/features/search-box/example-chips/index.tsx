import { useId } from "react"
import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import { Truncate } from "@/shared/ui/truncate"
import styles from "./styles.module.css"

export const EXAMPLES = ["groats", "office", "medical"] as const

export type ExampleChipsProps = {
  readonly disabled?: boolean
  readonly onPick: (text: string) => void
}

export function ExampleChips({ disabled = false, onPick }: ExampleChipsProps) {
  const { t } = useTranslation("search")
  const id = useId()
  return (
    <div className={styles.examples}>
      <span id={id} className={styles.caption}>
        {t("box.examples")}
      </span>
      <ul className={styles.list} aria-labelledby={id}>
        {EXAMPLES.map((example) => {
          const text = t(`box.example.${example}`)
          return (
            <li key={example} className={styles.item}>
              <button
                type="button"
                className={styles.chip}
                title={text}
                aria-disabled={disabled || undefined}
                onClick={() => onPick(text)}
              >
                <span className={styles.icon} aria-hidden="true">
                  <Icon name="search" size="sm" />
                </span>
                <Truncate className={styles.text}>{text}</Truncate>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
