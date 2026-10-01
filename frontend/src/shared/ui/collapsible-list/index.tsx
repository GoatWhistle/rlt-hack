import { type ReactNode, useId, useState } from "react"
import { useTranslation } from "react-i18next"
import { TextButton } from "@/shared/ui/text-button"
import styles from "./styles.module.css"

export type CollapsibleListProps<T> = {
  readonly items: readonly T[]
  readonly limit: number
  readonly itemKey: (item: T) => string
  readonly renderItem: (item: T) => ReactNode
}

export function CollapsibleList<T>({
  items,
  limit,
  itemKey,
  renderItem,
}: CollapsibleListProps<T>) {
  const { t } = useTranslation()
  const id = useId()
  const [expanded, setExpanded] = useState(false)
  const hidden = items.length - limit
  const visible = expanded || hidden <= 0 ? items : items.slice(0, limit)
  return (
    <>
      <ul id={id} className={styles.list}>
        {visible.map((item) => (
          <li key={itemKey(item)} className={styles.item}>
            {renderItem(item)}
          </li>
        ))}
      </ul>
      {hidden > 0 ? (
        <TextButton
          aria-expanded={expanded}
          aria-controls={id}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? t("action.showLess") : t("action.showAll", { count: items.length })}
        </TextButton>
      ) : null}
    </>
  )
}
