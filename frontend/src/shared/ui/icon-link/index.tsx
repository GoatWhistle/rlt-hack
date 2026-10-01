import { Link } from "react-router"
import { Icon, type IconName } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type IconLinkProps = {
  readonly to: string
  readonly icon: IconName
  readonly label: string
}

export function IconLink({ to, icon, label }: IconLinkProps) {
  return (
    <Link to={to} className={styles.link} aria-label={label}>
      <Icon name={icon} size="sm" />
    </Link>
  )
}
