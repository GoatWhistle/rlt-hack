export type Env = {
  readonly apiBaseUrl: string
  readonly demoMode: boolean
}

export const DEFAULT_API_BASE_URL = "/api"

export function readEnv(source: Readonly<Record<string, string | undefined>>): Env {
  const apiBaseUrl = source.VITE_API_BASE_URL?.trim()
  return {
    apiBaseUrl: apiBaseUrl ? apiBaseUrl : DEFAULT_API_BASE_URL,
    demoMode: source.VITE_DEMO_MODE?.trim() !== "false",
  }
}

export const env = readEnv(import.meta.env)
