import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import type { NewUpload } from "./gateway"
import { useUploadGateway } from "./gateway-context"
import { isProcessing } from "./model"

export const POLL_MS = 1000

export const uploadKeys = {
  all: ["uploads"] as const,
  detail: (uploadId: string) => ["uploads", uploadId] as const,
  lot: (uploadId: string, lotId: string) => ["uploads", uploadId, "lots", lotId] as const,
}

export function useUploads() {
  const gateway = useUploadGateway()
  return useQuery({
    queryKey: uploadKeys.all,
    queryFn: gateway.list,
    staleTime: 0,
    refetchInterval: (query) => (query.state.data?.some(isProcessing) ? POLL_MS : false),
  })
}

export function useUpload(uploadId: string) {
  const gateway = useUploadGateway()
  return useQuery({
    queryKey: uploadKeys.detail(uploadId),
    queryFn: () => gateway.get(uploadId),
    staleTime: 0,
    refetchInterval: (query) => {
      const data = query.state.data
      return data && isProcessing(data) ? POLL_MS : false
    },
  })
}

export function useLot(uploadId: string, lotId: string) {
  const gateway = useUploadGateway()
  return useQuery({
    queryKey: uploadKeys.lot(uploadId, lotId),
    queryFn: () => gateway.lot(uploadId, lotId),
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
