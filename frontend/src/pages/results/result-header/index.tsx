import { useTranslation } from "react-i18next"
import { type CsvColumn, csvFileName, toCsv } from "@/entities/recommendation/csv"
import type { Recommendation } from "@/entities/recommendation/model"
import { saveTextFile } from "@/shared/download/save-text-file"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { Icon } from "@/shared/ui/icon"
import { ChainIndicator } from "../chain-indicator"
import { statusText } from "../status"
import styles from "./styles.module.css"

export const CSV_TYPE = "text/csv;charset=utf-8"

export function ResultHeader({ recommendation }: { readonly recommendation: Recommendation }) {
  const { t } = useTranslation()
  const { products, companies } = recommendation
  const toCheck = companies.filter((company) => company.status === "check").length

  function download() {
    const columns: CsvColumn[] = [
      { header: t("results.csv.rank"), value: (_, rank) => rank },
      { header: t("results.csv.company"), value: (company) => company.name },
      { header: t("results.csv.inn"), value: (company) => company.inn },
      { header: t("results.csv.role"), value: (company) => company.role },
      { header: t("results.csv.status"), value: (company) => statusText(company, t) },
      {
        header: t("results.csv.matched"),
        value: (company) => `${company.matches.length}/${products.length}`,
      },
      { header: t("results.csv.purchases"), value: (company) => company.similarPurchases },
      { header: t("results.csv.wins"), value: (company) => company.wins },
      { header: t("results.csv.summary"), value: (company) => company.summary },
    ]
    saveTextFile(csvFileName(recommendation), toCsv(recommendation, columns), CSV_TYPE)
  }

  return (
    <header className={styles.header}>
      <div className={styles.titleRow}>
        <div className={styles.titles}>
          <Caption>
            {recommendation.lotLabel} · {recommendation.fileName}
          </Caption>
          <h1 className={styles.title}>{recommendation.requestTitle}</h1>
        </div>
        <Button variant="secondary" onClick={download}>
          <Icon name="download" />
          {t("results.header.downloadCsv")}
        </Button>
      </div>
      <div className={styles.meta}>
        <p className={styles.summary}>
          <span>{t("results.header.productCount", { count: products.length })}</span>
          <span>{t("results.header.companyCount", { count: companies.length })}</span>
          <span>{t("results.header.checkCount", { count: toCheck })}</span>
        </p>
        <ChainIndicator />
      </div>
    </header>
  )
}
