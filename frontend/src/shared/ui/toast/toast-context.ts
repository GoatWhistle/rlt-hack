import { createContext, use } from "react"

export type ToastTone = "info" | "success" | "error"

export type ToastInput = {
  readonly message: string
  readonly tone?: ToastTone
  readonly durationMs?: number
}

export type ToastApi = {
  readonly show: (toast: ToastInput) => number
  readonly dismiss: (id: number) => void
}

export const ToastContext = createContext<ToastApi | null>(null)

export function useToast(): ToastApi {
  const api = use(ToastContext)
  if (!api) throw new Error("useToast must be used within ToastProvider")
  return api
}
