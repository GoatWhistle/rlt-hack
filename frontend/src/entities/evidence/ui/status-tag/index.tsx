import type { ReactNode } from "react"
import type { CandidateStatus } from "@/entities/evidence/model"
import { Dot } from "@/shared/ui/dot"
import { Tag } from "@/shared/ui/tag"

export type StatusTagProps = {
  readonly status: CandidateStatus
  readonly children: ReactNode
}

export function StatusTag({ status, children }: StatusTagProps) {
  const recommended = status === "recommended"
  return (
    <Tag tone={recommended ? "accent" : "warning"}>
      <Dot
        shape={recommended ? "filled" : "hollow"}
        tone={recommended ? "accent" : "warning"}
      />
      {children}
    </Tag>
  )
}
