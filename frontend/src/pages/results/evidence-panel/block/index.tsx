import type { ReactNode } from "react"
import { Icon, type IconName, type IconTone } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type BlockProps = {
  readonly title: string
  readonly icon: IconName
  readonly tone: IconTone
  readonly aside?: ReactNode
  readonly children: ReactNode
}

export function Block({ title, icon, tone, aside, children }: BlockProps) {
  return (
    <section className={styles.block}>
      <div className={styles.heading}>
        <h3 className={styles.title}>
          <Icon name={icon} tone={tone} />
          {title}
        </h3>
        {aside}
      </div>
      {children}
    </section>
  )
}
