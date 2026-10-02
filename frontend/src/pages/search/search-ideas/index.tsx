import { useId } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { searchDraftPath } from "@/shared/config/paths"
import { SideTitle } from "../side-title"
import styles from "./styles.module.css"

export const IDEAS = ["paper", "laptops", "gloves", "roof", "cartridges"] as const

export function SearchIdeas() {
  const { t } = useTranslation("search")
  const id = useId()
  return (
    <section className={styles.ideas} aria-labelledby={id}>
      <SideTitle id={id}>{t("ideas.title")}</SideTitle>
      <ul className={styles.list}>
        {IDEAS.map((idea) => (
          <li key={idea}>
            <Link to={searchDraftPath(t(`ideas.items.${idea}`))} className={styles.idea}>
              {t(`ideas.items.${idea}`)}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
