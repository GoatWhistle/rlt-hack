import { useTranslation } from "react-i18next"
import { PurchaseRow } from "@/entities/evidence/ui/purchase-row"
import type { PurchaseHistory, QueryItem } from "@/entities/search/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import { CollapsibleList } from "@/shared/ui/collapsible-list"
import { Fold } from "@/shared/ui/fold"

export const RECORD_LIMIT = 3

export type HistoryBlockProps = {
  readonly history: PurchaseHistory
  readonly items: readonly QueryItem[]
}

export function HistoryBlock({ history, items }: HistoryBlockProps) {
  const { t } = useTranslation("search")
  const { list } = useFormatters()
  const names = new Map(items.map((item) => [item.id, item.name]))
  return (
    <Fold
      title={t("evidence.historyTitle")}
      aside={t("evidence.historyAside", {
        count: history.similarPurchases,
        wins: history.wins,
      })}
    >
      {history.records.length > 0 ? (
        <CollapsibleList
          items={history.records}
          limit={RECORD_LIMIT}
          itemKey={(record) => record.lotId}
          renderItem={(record) => {
            const matched = record.itemIds.flatMap((id) => names.get(id) ?? [])
            return (
              <>
                <PurchaseRow
                  title={t("evidence.lot", { id: record.lotId, title: record.title })}
                  outcome={record.outcome}
                />
                {matched.length > 0 ? (
                  <Caption>{t("evidence.recordItems", { names: list(matched) })}</Caption>
                ) : null}
              </>
            )
          }}
        />
      ) : (
        <Caption>{t("evidence.noRecords")}</Caption>
      )}
      <Caption>{t("evidence.historyNote")}</Caption>
    </Fold>
  )
}
