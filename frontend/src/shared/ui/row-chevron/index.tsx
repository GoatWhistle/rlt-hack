import { clsx } from "clsx"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export function RowChevron({ className }: { readonly className?: string }) {
  return (
    <span className={clsx(styles.chevron, className)} aria-hidden="true">
      <Icon name="chevron" />
    </span>
  )
}
