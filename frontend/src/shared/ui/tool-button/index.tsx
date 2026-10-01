import { clsx } from "clsx"
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, Ref } from "react"
import styles from "./styles.module.css"

export type ToolButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  readonly ref?: Ref<HTMLButtonElement>
}

export function ToolButton({ className, type = "button", ...props }: ToolButtonProps) {
  return <button type={type} className={clsx(styles.tool, className)} {...props} />
}

export type ToolLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  readonly href: string
}

export function ToolLink({ className, ...props }: ToolLinkProps) {
  return (
    <a
      target="_blank"
      rel="noopener noreferrer"
      className={clsx(styles.tool, className)}
      {...props}
    />
  )
}
