export type ApiErrorInit = {
  readonly status: number
  readonly code: string
  readonly message?: string
  readonly cause?: unknown
  readonly requestId?: string
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null

  constructor({ status, code, message, cause, requestId }: ApiErrorInit) {
    super(message ?? code, { cause })
    this.name = "ApiError"
    this.status = status
    this.code = code
    this.requestId = requestId ?? null
  }

  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
