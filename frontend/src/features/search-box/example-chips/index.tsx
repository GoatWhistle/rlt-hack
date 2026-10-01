import { useId } from "react"
import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export const EXAMPLES = ["groats", "office", "medical"] as const

export function ExampleChips({ onPick }: { readonly onPick: (text: string) => void }) {
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
                onClick={() => onPick(text)}
              >
                <span className={styles.icon} aria-hidden="true">
                  <Icon name="search" size="sm" />
                </span>
                <span className={styles.text}>{text}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
