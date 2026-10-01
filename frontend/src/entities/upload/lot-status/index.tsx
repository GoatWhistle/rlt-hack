import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { Dot } from "@/shared/ui/dot"
import { Icon } from "@/shared/ui/icon"
import { Tag, type TagTone } from "@/shared/ui/tag"
import type { LotStatus } from "../model"

const TONES: Record<LotStatus, TagTone> = {
  queued: "solid",
  ready: "solid",
  needsCheck: "warning",
  noCandidates: "tentative",
  failed: "danger",
}

const MARKS: Record<LotStatus, ReactNode> = {
  queued: <Icon name="clock" size="sm" />,
  ready: <Icon name="check" size="sm" />,
  needsCheck: <Icon name="warning" size="sm" />,
  noCandidates: <Dot shape="dashed" size="md" />,
  failed: <Icon name="close" size="sm" />,
}

export function LotStatusTag({ status }: { readonly status: LotStatus }) {
  const { t } = useTranslation("lots")
  return (
    <Tag tone={TONES[status]}>
      {MARKS[status]}
      {t(`status.${status}`)}
    </Tag>
  )
}
