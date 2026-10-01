import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import type { SearchResult } from "@/entities/search/model"
import { searchDraftPath, UPLOADS_PATH } from "@/shared/config/paths"
import { Button, ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { Icon } from "@/shared/ui/icon"
import { WorkspaceEmpty } from "@/shared/ui/workspace-layout"
import { ItemList } from "../item-list"
import styles from "./styles.module.css"

export const MIN_SPLIT_ITEMS = 2

export type EmptyResultProps = {
  readonly result: SearchResult
  readonly onEditQuery: () => void
}

export function EmptyResult({ result, onEditQuery }: EmptyResultProps) {
  const { t } = useTranslation("search")
  const { items, candidates } = result
  const split = items.length >= MIN_SPLIT_ITEMS ? items : []
  return (
    <WorkspaceEmpty
      list={
        items.length > 0 ? (
          <ItemList items={items} candidates={candidates} activeId={null} />
        ) : null
      }
    >
      <EmptyState
        icon="search"
        headingLevel={2}
        title={t("empty.title")}
        description={t("empty.text")}
        actions={
          <>
            <Button onClick={onEditQuery}>
              <Icon name="pencil" />
              {t("empty.action")}
            </Button>
            <ButtonLink variant="secondary" to={UPLOADS_PATH}>
              {t("empty.upload")}
            </ButtonLink>
          </>
        }
      >
        {split.length > 0 ? (
          <ul className={styles.split}>
            {split.map((item) => (
              <li key={item.id}>
                <Link to={searchDraftPath(item.name)} className={styles.link}>
                  <Icon name="search" size="sm" />
                  {t("empty.only", { name: item.name })}
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </EmptyState>
    </WorkspaceEmpty>
  )
}
