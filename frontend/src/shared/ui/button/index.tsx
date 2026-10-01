import { clsx } from "clsx"
import type { ButtonHTMLAttributes } from "react"
import { Link, type LinkProps } from "react-router"
import styles from "./styles.module.css"

export type ButtonVariant = "primary" | "secondary" | "strong"

const VARIANTS: Record<ButtonVariant, string | undefined> = {
  primary: styles.primary,
  secondary: styles.secondary,
  strong: styles.strong,
}

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  readonly variant?: ButtonVariant
}

export function Button({
  variant = "primary",
  type = "button",
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={clsx(styles.button, VARIANTS[variant], className)}
      {...props}
    />
  )
}

export type ButtonLinkProps = LinkProps & {
  readonly variant?: ButtonVariant
}

export function ButtonLink({ variant = "primary", className, ...props }: ButtonLinkProps) {
  return <Link className={clsx(styles.button, VARIANTS[variant], className)} {...props} />
}
