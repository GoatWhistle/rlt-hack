import { clsx } from "clsx"
import type { HTMLAttributes } from "react"
import styles from "./styles.module.css"

export type PageTitleSize = "page" | "record"

export type PageTitleProps = HTMLAttributes<HTMLHeadingElement> & {
  readonly size?: PageTitleSize
  readonly mono?: boolean
  readonly as?: "h1" | "h2"
}

export function PageTitle({
  size = "page",
  mono = false,
  as: Heading = "h1",
  className,
  ...props
}: PageTitleProps) {
  return (
    <Heading
      className={clsx(
        styles.title,
        size === "page" ? styles.page : styles.record,
        mono && styles.mono,
        className,
      )}
      {...props}
    />
  )
}
