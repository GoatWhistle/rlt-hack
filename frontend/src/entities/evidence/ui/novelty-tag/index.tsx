import { useTranslation } from "react-i18next"
import type { Novelty } from "@/entities/evidence/model"
import { Tag } from "@/shared/ui/tag"

export function NoveltyTag({ novelty }: { readonly novelty: Novelty }) {
  const { t } = useTranslation("evidence")
  if (novelty === "unknown") return null
  return <Tag tone={novelty === "new" ? "success" : "solid"}>{t(`novelty.${novelty}`)}</Tag>
}
