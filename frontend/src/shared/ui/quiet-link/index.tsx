import { clsx } from "clsx"
import type { AnchorHTMLAttributes } from "react"
import { Link, type LinkProps } from "react-router"
import styles from "./styles.module.css"

export function QuietLink({ className, ...props }: LinkProps) {
  return <Link className={clsx(styles.link, className)} {...props} />
}

export type QuietAnchorProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  readonly href: string
}

export function QuietAnchor({ className, ...props }: QuietAnchorProps) {
  return (
    <a
      target="_blank"
      rel="noopener noreferrer"
      className={clsx(styles.link, className)}
      {...props}
    />
  )
}
