import { clsx } from "clsx"
import { LoadingState } from "@/shared/ui/loading-state"
import styles from "./styles.module.css"

export type BoneProps = {
  readonly className?: string
}

export function Bone({ className }: BoneProps) {
  return <span className={clsx(styles.bone, className)} />
}

export type PageSkeletonProps = {
  readonly label: string
  readonly rows?: number
}

export function PageSkeleton({ label, rows = 4 }: PageSkeletonProps) {
  const lines = Array.from({ length: rows }, (_, index) => `row-${index}`)
  return (
    <LoadingState label={label}>
      <div className={styles.page}>
        <div className={styles.head}>
          <div className={styles.titles}>
            <Bone className={styles.title} />
            <Bone className={styles.caption} />
          </div>
          <Bone className={styles.action} />
        </div>
        <div className={styles.panel}>
          <div className={styles.columns}>
            <Bone className={styles.short} />
            <Bone className={styles.short} />
            <Bone className={styles.short} />
          </div>
          {lines.map((line) => (
            <div key={line} className={styles.row}>
              <Bone className={styles.wide} />
              <Bone className={styles.short} />
              <Bone className={styles.medium} />
            </div>
          ))}
        </div>
      </div>
    </LoadingState>
  )
}
