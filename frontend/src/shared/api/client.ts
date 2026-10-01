import { env } from "@/shared/config/env"
import { createHttpClient } from "./http-client"

export const apiClient = createHttpClient({ baseUrl: env.apiBaseUrl })
