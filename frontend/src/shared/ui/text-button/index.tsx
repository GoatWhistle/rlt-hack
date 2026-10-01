import { clsx } from "clsx"
import type { ButtonHTMLAttributes } from "react"
import styles from "./styles.module.css"

export type TextButtonProps = ButtonHTMLAttributes<HTMLButtonElement>

export function TextButton({ type = "button", className, ...props }: TextButtonProps) {
  return <button type={type} className={clsx(styles.button, className)} {...props} />
}
