import { clsx } from "clsx"
import type { ButtonHTMLAttributes, MouseEvent, ReactNode } from "react"
import { Link, type LinkProps } from "react-router"
import { Spinner } from "@/shared/ui/spinner"
import styles from "./styles.module.css"

export type ButtonVariant = "primary" | "secondary" | "strong"

const VARIANTS: Record<ButtonVariant, string | undefined> = {
  primary: styles.primary,
  secondary: styles.secondary,
  strong: styles.strong,
}

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  readonly variant?: ButtonVariant
  readonly pending?: boolean
  readonly pendingLabel?: ReactNode
}

function PendingFaces({
  pending,
  pendingLabel,
  children,
}: {
  readonly pending: boolean
  readonly pendingLabel: ReactNode
  readonly children: ReactNode
}) {
  return (
    <span className={styles.faces}>
      <span className={styles.face} data-shown={!pending} aria-hidden={pending}>
        {children}
      </span>
      <span className={styles.face} data-shown={pending} aria-hidden={!pending}>
        <Spinner />
        {pendingLabel}
      </span>
    </span>
  )
}

export function Button({
  variant = "primary",
  type = "button",
  className,
  pending = false,
  pendingLabel,
  children,
  onClick,
  ...props
}: ButtonProps) {
  function click(event: MouseEvent<HTMLButtonElement>) {
    if (pending) {
      event.preventDefault()
      return
    }
    onClick?.(event)
  }
  return (
    <button
      {...props}
      type={type}
      className={clsx(styles.button, VARIANTS[variant], className)}
      aria-disabled={pending || props["aria-disabled"] || undefined}
      aria-busy={pending || props["aria-busy"] || undefined}
      onClick={click}
    >
      {pendingLabel === undefined ? (
        children
      ) : (
        <PendingFaces pending={pending} pendingLabel={pendingLabel}>
          {children}
        </PendingFaces>
      )}
    </button>
  )
}

export type ButtonLinkProps = LinkProps & {
  readonly variant?: ButtonVariant
}

export function ButtonLink({ variant = "primary", className, ...props }: ButtonLinkProps) {
  return <Link className={clsx(styles.button, VARIANTS[variant], className)} {...props} />
}
