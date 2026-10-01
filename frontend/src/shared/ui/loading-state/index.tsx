import type { ReactNode } from "react"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export type LoadingStateProps = {
  readonly label: string
  readonly children?: ReactNode
}

export function LoadingState({ label, children }: LoadingStateProps) {
  return (
    <div role="status" aria-busy="true" className={children ? styles.reveal : undefined}>
      <VisuallyHidden>{label}</VisuallyHidden>
      {children ? <div aria-hidden="true">{children}</div> : null}
    </div>
  )
}
