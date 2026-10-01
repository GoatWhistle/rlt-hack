import { clsx } from "clsx"
import type { HTMLAttributes } from "react"
import { usePresence } from "@/shared/motion/use-presence"
import styles from "./styles.module.css"

export type TransitionPreset = "fade" | "scale" | "slide"

const PRESETS: Record<TransitionPreset, string | undefined> = {
  fade: styles.fade,
  scale: styles.scale,
  slide: styles.slide,
}

export type TransitionProps = HTMLAttributes<HTMLDivElement> & {
  readonly show: boolean
  readonly preset?: TransitionPreset
}

export function Transition({ show, preset = "fade", className, ...props }: TransitionProps) {
  const { isMounted, state, onAnimationEnd } = usePresence(show)
  if (!isMounted) return null
  return (
    <div
      data-state={state}
      className={clsx(PRESETS[preset], className)}
      onAnimationEnd={onAnimationEnd}
      {...props}
    />
  )
}
