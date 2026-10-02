import { Fragment } from "react"
import styles from "./styles.module.css"

const BREAK_AFTER = /(?<=[_\-.])/

export function FileName({ name }: { readonly name: string }) {
  const parts = name.split(BREAK_AFTER)
  return (
    <span className={styles.name}>
      {parts.map((part, index) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: file name parts never reorder
        <Fragment key={index}>
          {part}
          {index < parts.length - 1 ? <wbr /> : null}
        </Fragment>
      ))}
    </span>
  )
}
