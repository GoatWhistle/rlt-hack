import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router"
import { useRecommendationRequest } from "@/entities/recommendation/request"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { Dropzone } from "./dropzone"
import { FileCard } from "./file-card"
import { Steps } from "./steps"
import styles from "./styles.module.css"

export const RESULTS_PATH = "/results"

export function UploadPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const request = useRecommendationRequest()

  function submit(selected: File) {
    request.mutate(selected, {
      onSuccess: (recommendation) => navigate(RESULTS_PATH, { state: recommendation }),
    })
  }

  return (
    <div className={styles.page}>
      <div className={styles.intro}>
        <span className={styles.kicker}>
          <span className={styles.kickerDot} aria-hidden="true" />
          {t("upload.kicker")}
        </span>
        <h1 className={styles.title}>{t("upload.title")}</h1>
        <p className={styles.subtitle}>{t("upload.subtitle")}</p>
        <Steps />
      </div>
      <div className={styles.card}>
        <Dropzone hasFile={file !== null} onSelect={setFile} />
        {file ? (
          <>
            <FileCard file={file} onClear={() => setFile(null)} />
            <Button
              className={styles.submit}
              disabled={request.isPending}
              onClick={() => submit(file)}
            >
              {request.isPending ? t("upload.submitting") : t("upload.submit")}
              <Icon name="arrowRight" />
            </Button>
          </>
        ) : null}
        <p className={styles.privacy}>
          <Icon name="lock" size="sm" />
          {t("upload.privacy")}
        </p>
      </div>
    </div>
  )
}
