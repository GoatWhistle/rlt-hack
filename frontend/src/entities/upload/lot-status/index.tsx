import { useTranslation } from "react-i18next"
import { Tag, type TagTone } from "@/shared/ui/tag"
import type { LotStatus } from "../model"

const TONES: Record<LotStatus, TagTone> = {
  queued: "solid",
  ready: "success",
  needsCheck: "warning",
  noCandidates: "tentative",
}

export function LotStatusTag({ status }: { readonly status: LotStatus }) {
  const { t } = useTranslation("lots")
  return <Tag tone={TONES[status]}>{t(`status.${status}`)}</Tag>
}
