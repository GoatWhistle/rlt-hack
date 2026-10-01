import { useTranslation } from "react-i18next"
import { type Contacts, hasContacts } from "@/entities/evidence/model"
import { Caption } from "@/shared/ui/caption"
import { type Fact, FactList } from "@/shared/ui/fact-list"

function phoneHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, "")}`
}

export function ContactList({ contacts }: { readonly contacts?: Contacts }) {
  const { t } = useTranslation("evidence")
  if (!contacts || !hasContacts(contacts)) return <Caption>{t("contacts.none")}</Caption>
  const { site, email, phone } = contacts
  const facts: Fact[] = [
    ...(site
      ? [{ key: "site", term: t("contacts.site"), value: <a href={site}>{site}</a> }]
      : []),
    ...(email
      ? [
          {
            key: "email",
            term: t("contacts.email"),
            value: <a href={`mailto:${email}`}>{email}</a>,
          },
        ]
      : []),
    ...(phone
      ? [
          {
            key: "phone",
            term: t("contacts.phone"),
            value: <a href={phoneHref(phone)}>{phone}</a>,
          },
        ]
      : []),
  ]
  return <FactList facts={facts} />
}
