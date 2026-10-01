import { clsx } from "clsx"
import { Link } from "react-router"
import { Icon, type IconName } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type IconLinkProps = {
  readonly to?: string
  readonly icon: IconName
  readonly label: string
  readonly shortcut?: string
}

export function IconLink({ to, icon, label, shortcut }: IconLinkProps) {
  if (!to) {
    return (
      <span className={clsx(styles.link, styles.disabled)} aria-hidden="true">
        <Icon name={icon} size="sm" />
      </span>
    )
  }
  return (
    <Link
      to={to}
      className={styles.link}
      aria-label={label}
      aria-keyshortcuts={shortcut}
      title={shortcut ? `${label} (${shortcut})` : undefined}
    >
      <Icon name={icon} size="sm" />
    </Link>
  )
}
