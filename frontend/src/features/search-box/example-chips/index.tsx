import { useId } from "react"
import { useTranslation } from "react-i18next"
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
            <li key={example}>
              <button type="button" className={styles.chip} onClick={() => onPick(text)}>
                {text}
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
