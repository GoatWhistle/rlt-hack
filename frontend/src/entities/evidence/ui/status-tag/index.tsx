import { clsx } from "clsx"
import type { ReactNode } from "react"
import type { CandidateStatus } from "@/entities/evidence/model"
import { Tag } from "@/shared/ui/tag"
import styles from "./styles.module.css"

export type StatusTagProps = {
  readonly status: CandidateStatus
  readonly children: ReactNode
}

export function StatusTag({ status, children }: StatusTagProps) {
  const recommended = status === "recommended"
  return (
    <Tag tone={recommended ? "success" : "warning"}>
      <span
        aria-hidden="true"
        className={clsx(styles.dot, recommended ? styles.filled : styles.hollow)}
      />
      {children}
    </Tag>
  )
}
