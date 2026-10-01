import styles from "./styles.module.css"

export type SkipLinkProps = {
  readonly targetId: string
  readonly label: string
}

export function SkipLink({ targetId, label }: SkipLinkProps) {
  return (
    <a className={styles.skipLink} href={`#${targetId}`}>
      {label}
    </a>
  )
}
