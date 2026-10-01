import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import type { Locale } from "@/shared/i18n/locale"
import { useLocale } from "@/shared/i18n/locale-provider"
import type { NewUpload } from "./gateway"
import { useUploadGateway } from "./gateway-context"
import { isProcessing } from "./model"

export const POLL_MS = 1000

export const uploadKeys = {
  all: ["uploads"] as const,
  list: (locale: Locale) => ["uploads", locale] as const,
  detail: (locale: Locale, uploadId: string) => ["uploads", locale, uploadId] as const,
  lot: (locale: Locale, uploadId: string, lotId: string) =>
    ["uploads", locale, uploadId, "lots", lotId] as const,
}

const LOCALE_PART = 1

export function sameButLocale(
  previous: readonly unknown[] | undefined,
  next: readonly unknown[],
): boolean {
  if (!previous || previous.length !== next.length) return false
  return previous.every((part, index) => index === LOCALE_PART || part === next[index])
}

function keptAcrossLocales<T>(key: readonly unknown[]) {
  return (
    previous: T | undefined,
    query: { readonly queryKey: readonly unknown[] } | undefined,
  ) => (sameButLocale(query?.queryKey, key) ? previous : undefined)
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

export function useUpload(uploadId: string) {
  const gateway = useUploadGateway()
  const { locale } = useLocale()
  return useQuery({
    queryKey: uploadKeys.detail(locale, uploadId),
    queryFn: () => gateway.get(uploadId),
    placeholderData: keptAcrossLocales(uploadKeys.detail(locale, uploadId)),
    staleTime: 0,
    refetchInterval: (query) => {
      const data = query.state.data
      return data && isProcessing(data) ? POLL_MS : false
    },
  })
}

export function useLot(uploadId: string, lotId: string) {
  const gateway = useUploadGateway()
  const { locale } = useLocale()
  return useQuery({
    queryKey: uploadKeys.lot(locale, uploadId, lotId),
    queryFn: () => gateway.lot(uploadId, lotId),
    placeholderData: keptAcrossLocales(uploadKeys.lot(locale, uploadId, lotId)),
    refetchInterval: (query) => (query.state.data?.lot.status === "queued" ? POLL_MS : false),
  })
}

export function useCreateUpload() {
  const gateway = useUploadGateway()
  const client = useQueryClient()
  return useMutation({
    mutationFn: (upload: NewUpload) => gateway.create(upload),
    onSuccess: () => client.invalidateQueries({ queryKey: uploadKeys.all }),
  })
}
