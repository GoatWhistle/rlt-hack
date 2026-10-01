import styles from "./styles.module.css"

export const BRAND_MARK_PATHS = {
  letter: "M20 8h12v37h32v11l-8 8H8V20Z",
  facet: "m52 8 14 14-14 14-14-14Z",
} as const

export function BrandMark() {
  return (
    <svg viewBox="0 0 72 72" className={styles.mark} aria-hidden="true" focusable="false">
      <path className={styles.letter} d={BRAND_MARK_PATHS.letter} />
      <path className={styles.facet} d={BRAND_MARK_PATHS.facet} />
    </svg>
  )
}
