import type { ReactNode } from "react"
import { Link } from "react-router"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type BackLinkProps = {
  readonly to: string
  readonly children: ReactNode
}

export function BackLink({ to, children }: BackLinkProps) {
  return (
    <Link to={to} className={styles.link}>
      <Icon name="arrowLeft" size="sm" />
      <span className={styles.text}>{children}</span>
    </Link>
  )
}
