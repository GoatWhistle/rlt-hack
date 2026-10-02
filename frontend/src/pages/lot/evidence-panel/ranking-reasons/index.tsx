import { useTranslation } from "react-i18next"
import type { Company } from "@/entities/recommendation/model"
import { Icon } from "@/shared/ui/icon"
import { Stack } from "@/shared/ui/stack"
import styles from "./styles.module.css"

export function RankingReasons({ company }: { readonly company: Company }) {
  const { t } = useTranslation("lot")
  if (!company.rankingReasons?.length) return null
  return (
    <section className={styles.section} aria-label={t("ranking.title")}>
      <p className={styles.label}>{t("ranking.title")}</p>
      <Stack as="ul">
        {company.rankingReasons.map((reason) => (
          <li key={reason} className={styles.reason}>
            <Icon name="check" size="sm" />
            <span>
              {reason === "category" && company.similarPurchases !== null
                ? t("ranking.categoryCount", { count: company.similarPurchases })
                : t(`ranking.${reason}`)}
            </span>
          </li>
        ))}
      </Stack>
    </section>
  )
}
