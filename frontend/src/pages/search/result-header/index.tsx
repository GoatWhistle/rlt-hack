import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { SearchResult } from "@/entities/search/model"
import { useSearchShortlist } from "@/entities/shortlist/store"
import { SearchExportDialog } from "@/features/export-results"
import { SEARCH_PATH, searchDraftPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { BackLink } from "@/shared/ui/back-link"
import { Button, ButtonLink } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export function ResultHeader({ result }: { readonly result: SearchResult }) {
  const { t } = useTranslation("search")
  const { dateTime } = useFormatters()
  const shortlist = useSearchShortlist(result.searchId)
  const [exporting, setExporting] = useState(false)
  const recommended = result.candidates.filter((item) => item.status === "recommended").length
  const facts = [
    t("items.count", { count: result.items.length }),
    t("recent.candidates", { count: result.candidates.length }),
    ...(recommended > 0 ? [t("recent.recommended", { count: recommended })] : []),
    t("header.created", { date: dateTime(result.createdAt) }),
  ]
  return (
    <header className={styles.header}>
      <div className={styles.back}>
        <BackLink to={SEARCH_PATH}>{t("header.back")}</BackLink>
      </div>
      <div className={styles.query}>
        <p className={styles.eyebrow}>{t("header.label")}</p>
        <h1 className={styles.title} title={result.query.text}>
          {result.query.text}
        </h1>
      </div>
      <p className={styles.meta}>
        {facts.map((fact) => (
          <span key={fact} className={styles.fact}>
            {fact}
          </span>
        ))}
      </p>
      <div className={styles.actions}>
        <ButtonLink variant="secondary" to={searchDraftPath(result.query.text)}>
          <Icon name="pencil" />
          {t("header.edit")}
        </ButtonLink>
        {result.candidates.length > 0 ? (
          <Button variant="secondary" onClick={() => setExporting(true)}>
            <Icon name="download" />
            {t("header.export")}
          </Button>
        ) : null}
      </div>
      <SearchExportDialog
        open={exporting}
        onClose={() => setExporting(false)}
        result={result}
        chosen={shortlist.ids}
      />
    </header>
  )
}
