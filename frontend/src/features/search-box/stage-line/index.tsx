import { useTranslation } from "react-i18next"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import type { SearchStage } from "../use-stage"
import styles from "./styles.module.css"

const ANNOUNCED: readonly SearchStage[] = ["parse", "slow"]

export function StageLine({ stage }: { readonly stage: SearchStage | null }) {
  const { t } = useTranslation("search")
  const announced = stage && ANNOUNCED.includes(stage) ? t(`box.stage.${stage}`) : ""
  return (
    <>
      <VisuallyHidden role="status">{announced}</VisuallyHidden>
      {stage ? (
        <span
          key={stage}
          className={styles.stage}
          data-slow={stage === "slow"}
          aria-hidden="true"
        >
          {t(`box.stage.${stage}`)}
        </span>
      ) : null}
    </>
  )
}

export function SweepBar() {
  return (
    <span className={styles.track} aria-hidden="true">
      <span className={styles.sweep} />
    </span>
  )
}
