import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router"
import { useRecommendationRequest } from "@/entities/recommendation/request"
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
      <h1 className={styles.title}>{t("upload.title")}</h1>
      <p className={styles.subtitle}>{t("upload.subtitle")}</p>
      <Dropzone onSelect={setFile} />
      {file ? <FileCard file={file} pending={request.isPending} onSubmit={submit} /> : null}
      <Steps />
    </div>
  )
}
