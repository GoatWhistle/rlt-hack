export type Env = {
  readonly apiBaseUrl: string
}

export const DEFAULT_API_BASE_URL = "/api"

export function readEnv(source: Readonly<Record<string, string | undefined>>): Env {
  const apiBaseUrl = source.VITE_API_BASE_URL?.trim()
  return { apiBaseUrl: apiBaseUrl ? apiBaseUrl : DEFAULT_API_BASE_URL }
}

export const env = readEnv(import.meta.env)
