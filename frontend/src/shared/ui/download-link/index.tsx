import type { ReactNode } from "react"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type DownloadLinkProps = {
  readonly href: string
  readonly children: ReactNode
}

export function DownloadLink({ href, children }: DownloadLinkProps) {
  return (
    <a href={href} download className={styles.link}>
      <Icon name="download" />
      {children}
    </a>
  )
}
