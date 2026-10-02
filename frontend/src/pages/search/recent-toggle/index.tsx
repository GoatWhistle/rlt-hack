import type { Ref } from "react"
import { useTranslation } from "react-i18next"
import { useSearchHistory } from "@/entities/search/queries"
import { CountBadge } from "@/shared/ui/count-badge"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type RecentRevealProps = {
  readonly open: boolean
  readonly controls: string
  readonly ref?: Ref<HTMLButtonElement>
  readonly onOpen: () => void
}

export function RecentReveal({ open, controls, ref, onOpen }: RecentRevealProps) {
  const { t } = useTranslation("search")
  const recent = useSearchHistory()
  const count = recent.data?.pages[0]?.total ?? 0
  return (
    <button
      ref={ref}
      type="button"
      className={styles.reveal}
      data-state={open ? "hidden" : "shown"}
      inert={open}
      aria-hidden={open || undefined}
      aria-expanded={open}
      aria-controls={controls}
      onClick={onOpen}
    >
      {t("recent.title")}
      {count > 0 ? <CountBadge value={count} /> : null}
    </button>
  )
}

export type RecentCollapseProps = {
  readonly controls: string
  readonly onCollapse: () => void
}

export function RecentCollapse({ controls, onCollapse }: RecentCollapseProps) {
  const { t } = useTranslation("search")
  return (
    <button
      type="button"
      className={styles.collapse}
      aria-expanded={true}
      aria-controls={controls}
      aria-label={t("recent.collapse")}
      title={t("recent.collapse")}
      onClick={onCollapse}
    >
      <span className={styles.up} aria-hidden="true">
        <Icon name="chevron" size="sm" />
      </span>
    </button>
  )
}
