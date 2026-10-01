import { useTranslation } from "react-i18next"
import { IconButton } from "@/shared/ui/icon-link"
import styles from "./styles.module.css"

export type CandidatePagerProps = {
  readonly index: number
  readonly total: number
  readonly onPrev?: () => void
  readonly onNext?: () => void
}

export function CandidatePager({ index, total, onPrev, onNext }: CandidatePagerProps) {
  const { t } = useTranslation("candidate")
  return (
    <nav className={styles.pager} aria-label={t("pager.label")}>
      <IconButton icon="arrowLeft" label={t("pager.prev")} onClick={onPrev} />
      <span className={styles.position}>{t("pager.position", { index, total })}</span>
      <IconButton icon="arrowRight" label={t("pager.next")} onClick={onNext} />
    </nav>
  )
}
