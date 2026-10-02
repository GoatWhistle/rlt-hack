import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { keptAcrossLocales } from "@/shared/api/locale-keys"
import type { Locale } from "@/shared/i18n/locale"
import { useLocale } from "@/shared/i18n/locale-provider"
import type { NewUpload } from "./gateway"
import { useUploadGateway } from "./gateway-context"
import { isProcessing, type LotDetail, type UploadDetail, type UploadSummary } from "./model"

export { sameButLocale } from "@/shared/api/locale-keys"

export const POLL_MS = 1000
export const DETAIL_POLL_MS = 5000

export const uploadKeys = {
  all: ["uploads"] as const,
  list: (locale: Locale) => ["uploads", locale] as const,
  detail: (locale: Locale, uploadId: string) => ["uploads", locale, uploadId] as const,
  progress: (uploadId: string) => ["upload-progress", uploadId] as const,
  lot: (locale: Locale, uploadId: string, lotId: string) =>
    ["uploads", locale, uploadId, "lots", lotId] as const,
}

export function useUploads() {
  const gateway = useUploadGateway()
  const { locale } = useLocale()
  return useQuery({
    queryKey: uploadKeys.list(locale),
    queryFn: gateway.list,
    placeholderData: keptAcrossLocales(uploadKeys.list(locale)),
    staleTime: 0,
    refetchInterval: (query) => (query.state.data?.some(isProcessing) ? POLL_MS : false),
  })
}

export function withProgress(
  detail: UploadDetail | undefined,
  progress: UploadSummary,
): UploadDetail | undefined {
  if (!detail || progress.processed <= detail.processed) return detail
  return { ...detail, processed: progress.processed, counts: progress.counts }
}

function useUploadProgress(uploadId: string, enabled: boolean) {
  const gateway = useUploadGateway()
  const light = gateway.summary
  return useQuery({
    queryKey: uploadKeys.progress(uploadId),
    queryFn: () => (light ? light(uploadId) : Promise.reject(new Error("no summary"))),
    enabled: enabled && light !== undefined,
    staleTime: 0,
    refetchInterval: POLL_MS,
  })
}

export function useUpload(uploadId: string) {
  const gateway = useUploadGateway()
  const client = useQueryClient()
  const { locale } = useLocale()
  const light = gateway.summary !== undefined
  const detail = useQuery({
    queryKey: uploadKeys.detail(locale, uploadId),
    queryFn: () => gateway.get(uploadId),
    placeholderData: keptAcrossLocales(uploadKeys.detail(locale, uploadId)),
    staleTime: 0,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data || !isProcessing(data)) return false
      return light ? DETAIL_POLL_MS : POLL_MS
    },
  })
  const processing = detail.data !== undefined && isProcessing(detail.data)
  const latest = useUploadProgress(uploadId, processing).data
  useEffect(() => {
    if (!latest) return
    const key = uploadKeys.detail(locale, uploadId)
    client.setQueryData<UploadDetail>(key, (current) => withProgress(current, latest))
    if (!isProcessing(latest)) void client.invalidateQueries({ queryKey: key, exact: true })
  }, [client, locale, uploadId, latest])
  return detail
}

export const LOT_PART = 4

export function sameUpload(
  previous: readonly unknown[] | undefined,
  next: readonly unknown[],
): boolean {
  if (!previous || previous.length !== next.length) return false
  return previous.every((part, index) => index === LOT_PART || part === next[index])
}

export function useLot(uploadId: string, lotId: string) {
  const gateway = useUploadGateway()
  const { locale } = useLocale()
  const key = uploadKeys.lot(locale, uploadId, lotId)
  const acrossLocales = keptAcrossLocales<LotDetail>(key)
  return useQuery({
    queryKey: key,
    queryFn: () => gateway.lot(uploadId, lotId),
    placeholderData: (previous, query) =>
      acrossLocales(previous, query) ??
      (sameUpload(query?.queryKey, key) ? previous : undefined),
    refetchInterval: (query) => (query.state.data?.lot.status === "queued" ? POLL_MS : false),
  })
}

export function useCreateUpload(onCreated?: (upload: UploadSummary) => void) {
  const gateway = useUploadGateway()
  const client = useQueryClient()
  return useMutation({
    mutationFn: (upload: NewUpload) => gateway.create(upload),
    onSuccess: (upload) => {
      void client.invalidateQueries({ queryKey: uploadKeys.all })
      onCreated?.(upload)
    },
    meta: { silent: true },
  })
}
