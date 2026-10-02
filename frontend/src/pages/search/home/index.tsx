import { useId, useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate, useSearchParams } from "react-router"
import { DEFAULT_REGION_CODE, isRegionCode } from "@/entities/evidence/regions"
import type { UploadSummary } from "@/entities/upload/model"
import { AttachButton } from "@/features/file-intake/attach-button"
import { CheckDisclosure } from "@/features/file-intake/check-disclosure"
import { FileChip } from "@/features/file-intake/file-chip"
import { FileInput, FormatsHint, useFilePicker } from "@/features/file-intake/file-picker"
import { ItemsAttachment } from "@/features/file-intake/items-attachment"
import { sendable } from "@/features/file-intake/model"
import { useFileIntake } from "@/features/file-intake/use-file-intake"
import { useWindowDrop } from "@/features/file-intake/use-window-drop"
import { type Attachment, SearchBox } from "@/features/search-box"
import { lotPath, SEARCH_TEXT_PARAM, uploadPath } from "@/shared/config/paths"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { PageTitle } from "@/shared/ui/page-title"
import { LatestStrip } from "../latest-strip"
import { SearchIdeas } from "../search-ideas"
import styles from "./styles.module.css"

function regionFrom(param: string | null): string {
  if (param === "") return ""
  return param !== null && isRegionCode(param) ? param : DEFAULT_REGION_CODE
}

export function foundPath(result: UploadSummary, lots: readonly string[]): string {
  const [only] = lots
  return lots.length === 1 && only ? lotPath(result.id, only) : uploadPath(result.id)
}

function useAttachment(fieldId: string) {
  const files = useFileIntake()
  const picker = useFilePicker()
  const dropping = useWindowDrop(files.attach)
  const { intake } = files
  const [itemsFile, setItemsFile] = useState<File | undefined>()
  const notices = sendable(intake)
  const upload = notices && itemsFile ? { ...notices, itemsFile } : notices
  const remove = () => {
    files.clear()
    setItemsFile(undefined)
    document.getElementById(fieldId)?.focus()
  }
  const attachment: Attachment = {
    upload,
    reading: intake?.status === "reading",
    needsText: intake !== null && intake.status !== "reading" && upload === null,
    dropping,
    chip: <FileChip intake={intake} onRemove={remove} onReplace={picker.open} />,
    tool: <AttachButton attached={intake !== null} onClick={picker.open} />,
    hint: <FormatsHint />,
  }
  const items = notices ? <ItemsAttachment file={itemsFile} onChange={setItemsFile} /> : null
  return {
    attachment,
    intake,
    items,
    input: <FileInput picker={picker} onFile={files.attach} />,
  }
}

export function SearchPage() {
  const { t } = useTranslation("search")
  const { t: common } = useTranslation()
  useDocumentTitle(common("title.search"))
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const titleId = useId()
  const fieldId = useId()
  const { attachment, intake, items, input } = useAttachment(fieldId)
  const region = params.get("region")
  const draft = params.get(SEARCH_TEXT_PARAM) ?? ""
  return (
    <section className={styles.page} aria-labelledby={titleId}>
      <div className={styles.intro}>
        <PageTitle id={titleId}>{t("home.title")}</PageTitle>
        <p className={styles.lead}>{t("home.lead")}</p>
      </div>
      <div className={styles.layout}>
        <div className={styles.query}>
          <SearchBox
            key={draft}
            autoFocus
            shortcut
            inputId={fieldId}
            initialText={draft}
            initialRegion={regionFrom(region)}
            attachment={attachment}
            onFound={(result, lots) =>
              navigate(foundPath(result, lots), { viewTransition: true })
            }
          />
          {input}
          <CheckDisclosure intake={intake} />
          {items}
        </div>
        <aside className={styles.side}>
          <SearchIdeas />
          <LatestStrip />
        </aside>
      </div>
    </section>
  )
}
