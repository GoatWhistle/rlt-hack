import type { ReactNode } from "react"
import { Link } from "react-router"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type ArrowLinkProps = {
  readonly to: string
  readonly children: ReactNode
}

export function ArrowLink({ to, children }: ArrowLinkProps) {
  return (
    <Link to={to} className={styles.link}>
      {children}
      <Icon name="arrowRight" size="sm" />
    </Link>
  )
}
