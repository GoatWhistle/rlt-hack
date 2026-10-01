import { fileURLToPath } from "node:url"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export const alias = {
  "@": fileURLToPath(new URL("./src", import.meta.url)),
  "@tests": fileURLToPath(new URL("./tests", import.meta.url)),
}

const apiProxy = process.env.VITE_API_PROXY

// biome-ignore lint/style/noDefaultExport: Vite reads its configuration from the default export
export default defineConfig({
  plugins: [react()],
  resolve: { alias },
  server: {
    port: 5173,
    proxy: apiProxy ? { "/api": { target: apiProxy, changeOrigin: true } } : undefined,
  },
})
