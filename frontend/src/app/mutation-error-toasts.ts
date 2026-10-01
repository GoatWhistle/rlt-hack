import type { QueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { useToast } from "@/shared/ui/toast/toast-context"

export function useMutationErrorToasts(queryClient: QueryClient): void {
  const { show } = useToast()
  const errorMessage = useErrorMessage()
  useEffect(
    () =>
      queryClient.getMutationCache().subscribe((event) => {
        if (event.type !== "updated" || event.action.type !== "error") return
        if (event.mutation.meta?.silent === true) return
        show({ tone: "error", message: errorMessage(event.action.error) })
      }),
    [queryClient, show, errorMessage],
  )
}
