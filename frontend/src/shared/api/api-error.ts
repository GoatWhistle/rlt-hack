export type ApiErrorInit = {
  readonly status: number
  readonly code: string
  readonly message?: string
  readonly cause?: unknown
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor({ status, code, message, cause }: ApiErrorInit) {
    super(message ?? code, { cause })
    this.name = "ApiError"
    this.status = status
    this.code = code
  }

  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
