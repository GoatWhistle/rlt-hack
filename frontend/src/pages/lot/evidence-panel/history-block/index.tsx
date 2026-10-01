import { useTranslation } from "react-i18next"
import type { Company } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { CollapsibleList } from "@/shared/ui/collapsible-list"
import { Stack } from "@/shared/ui/stack"
import { Block } from "../block"

export function HistoryBlock({ company }: { readonly company: Company }) {
  const { t } = useTranslation("lot")
  const history = company.history
  if (!history) return null
  return (
    <>
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
      {company.catalog?.length ? (
        <Block title={t("history.catalog")}>
          <Stack as="ul">
            {company.catalog.map((item) => (
              <li key={item.url}>
                <a href={item.url}>{item.name}</a>
                <Caption>{t("history.checkedAt", { date: item.checkedAt })}</Caption>
              </li>
            ))}
          </Stack>
        </Block>
      ) : null}
    </>
  )
}
