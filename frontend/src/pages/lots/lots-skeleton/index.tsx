import { useTranslation } from "react-i18next"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

const ROWS = Array.from({ length: 8 }, (_, index) => index)

export function LotsSkeleton() {
  const { t } = useTranslation("lots")
  return (
    <div className={styles.skeleton} role="status" aria-busy="true">
      <VisuallyHidden>{t("loading")}</VisuallyHidden>
      <div className={styles.blocks} aria-hidden="true">
        <div className={styles.header}>
          <span className={styles.back} />
          <div className={styles.top}>
            <div className={styles.titles}>
              <span className={styles.title} />
              <span className={styles.meta} />
            </div>
            <span className={styles.action} />
          </div>
          <span className={styles.strip} />
          <span className={styles.legend} />
        </div>
        <div className={styles.controls}>
          <span className={styles.search} />
          <span className={styles.segments} />
        </div>
        <div className={styles.table}>
          <div className={styles.head} />
          {ROWS.map((row) => (
            <div key={row} className={styles.row}>
              <span className={styles.box} />
              <span className={styles.lines}>
                <span className={styles.line} />
                <span className={styles.short} />
              </span>
              <span className={styles.tag} />
              <span className={styles.cell} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
