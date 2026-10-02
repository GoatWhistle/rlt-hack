import { useTranslation } from "react-i18next"
import { OfferGrid } from "@/entities/evidence/ui/offer-grid"
import type { Company } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { CollapsibleList } from "@/shared/ui/collapsible-list"
import { PanelBlock as Block } from "@/shared/ui/panel-block"
import { Stack } from "@/shared/ui/stack"
import { catalogOfferView } from "./catalog"

export const CATALOG_LIMIT = 4

export function HistoryBlock({
  company,
  showExamples = true,
}: {
  readonly company: Company
  readonly showExamples?: boolean
}) {
  const { t } = useTranslation("lot")
  const history = company.history
  if (!history) return null
  return (
    <>
      {showExamples ? (
        <Block title={t("history.title")}>
          <Stack>
            <Caption>{t("history.source", { category: history.category })}</Caption>
            {history.lastDate ? (
              <Caption>{t("history.lastDate", { date: history.lastDate })}</Caption>
            ) : null}
            <CollapsibleList
              items={history.examples}
              limit={3}
              itemKey={(example) => example}
              renderItem={(example) => <p>{example}</p>}
            />
            <Caption>{t("history.note")}</Caption>
          </Stack>
        </Block>
      ) : null}
      {company.catalog?.length ? (
        <Block title={t("history.catalog")}>
          <OfferGrid
            entries={company.catalog.map((item) => ({ offer: catalogOfferView(item) }))}
            label={t("history.catalog")}
            limit={CATALOG_LIMIT}
            ribbon
          />
        </Block>
      ) : null}
    </>
  )
}
