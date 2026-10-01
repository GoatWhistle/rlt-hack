import gb from "./gb.svg"
import ru from "./ru.svg"
import styles from "./styles.module.css"

export type FlagCode = "ru" | "gb"

const SOURCES: Record<FlagCode, string> = { ru, gb }

export type FlagProps = {
  readonly code: FlagCode
}

export function Flag({ code }: FlagProps) {
  return <img className={styles.flag} src={SOURCES[code]} alt="" width={20} height={15} />
}
