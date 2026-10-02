import { useTranslation } from "react-i18next"
import { useMatchFigure } from "@/entities/evidence/labels"
import {
  type CandidateView,
  type ItemView,
  type RowView,
  rowsOf,
} from "@/entities/evidence/view"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import { CollapsibleList } from "@/shared/ui/collapsible-list"
import { Fold } from "@/shared/ui/fold"
import { PanelBlock } from "@/shared/ui/panel-block"
import { Stack } from "@/shared/ui/stack"
import { HistoryChips } from "../history-chips"
import { MatchRow } from "../match-row"
import { type OfferEntry, OfferGrid } from "../offer-grid"
import { PurchaseRow } from "../purchase-row"

export const PURCHASE_LIMIT = 3

export type BlockProps = {
  readonly candidate: CandidateView
  readonly items: readonly ItemView[]
}

export const OFFER_LIMIT = 4

function hasCard(row: RowView): boolean {
  return row.match?.offer !== undefined && row.match.basis !== "inferred"
}

export function offerEntries(rows: readonly RowView[]): OfferEntry[] {
  return rows.flatMap(({ item, match }) =>
    match?.offer && hasCard({ item, match })
      ? [
          {
            key: item.id,
            offer: match.offer,
            link: { itemName: item.name, basis: match.basis },
          },
        ]
      : [],
  )
}

export function MatchBlock({
  candidate,
  items,
  focusItemId,
}: BlockProps & { readonly focusItemId?: string }) {
  const { t } = useTranslation("candidate")
  const figure = useMatchFigure()(candidate.matches, items.length)
  const rows = rowsOf(candidate, items)
  const offers = offerEntries(rows)
  const rest = rows.filter((row) => !hasCard(row))
  return (
    <PanelBlock
      title={t("panel.matchesTitle")}
      aside={figure.note ? `${figure.value} ${figure.note}` : figure.value}
    >
      {offers.length > 0 ? (
        <OfferGrid
          entries={offers}
          label={t("panel.offersLabel")}
          limit={OFFER_LIMIT}
          focusKey={focusItemId}
          ribbon
        />
      ) : null}
      {rest.length > 0 ? (
        <Stack as="ul">
          {rest.map(({ item, match }) => (
            <li key={item.id}>
              <MatchRow name={item.name} basis={match?.basis} source={match?.source} />
            </li>
          ))}
        </Stack>
      ) : null}
      <Caption>{t("panel.matchesHint")}</Caption>
    </PanelBlock>
  )
}

export function HistoryBlock({ candidate, items }: BlockProps) {
  const { t } = useTranslation("candidate")
  const { list } = useFormatters()
  const names = new Map(items.map((item) => [item.id, item.name]))
  return (
    <Fold
      title={t("panel.historyTitle")}
      aside={<HistoryChips similar={candidate.similarPurchases} wins={candidate.wins} />}
    >
      {candidate.purchases.length > 0 ? (
        <CollapsibleList
          items={candidate.purchases}
          limit={PURCHASE_LIMIT}
          itemKey={(purchase) => purchase.key}
          renderItem={(purchase) => {
            const matched = purchase.itemIds.flatMap((id) => names.get(id) ?? [])
            return (
              <>
                <PurchaseRow
                  lead={purchase.year?.toString()}
                  title={
                    purchase.lotId
                      ? t("panel.lot", { id: purchase.lotId, title: purchase.title })
                      : purchase.title
                  }
                  href={purchase.url}
                  outcome={purchase.outcome}
                />
                {matched.length > 0 ? (
                  <Caption>{t("panel.recordItems", { names: list(matched) })}</Caption>
                ) : null}
              </>
            )
          }}
        />
      ) : (
        <Caption>{t("panel.noRecords")}</Caption>
      )}
      <Caption>{t("panel.historyNote")}</Caption>
    </Fold>
  )
}
