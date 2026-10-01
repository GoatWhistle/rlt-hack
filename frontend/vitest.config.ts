import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"
import { alias } from "./vite.config"

const shared = { globals: false, css: false, testTimeout: 15_000 }

// biome-ignore lint/style/noDefaultExport: Vitest reads its configuration from the default export
export default defineConfig({
  plugins: [react()],
  resolve: { alias },
  test: {
    coverage: {
      provider: "v8",
      reporter: ["text-summary", "json-summary", "html"],
      include: ["src/**/*.{ts,tsx}", "scripts/**/*.ts"],
      exclude: ["src/main.tsx", "src/**/*.d.ts", "scripts/checks/run.ts"],
      thresholds: { lines: 80, functions: 80, branches: 80, statements: 80 },
    },
    projects: [
      {
        plugins: [react()],
        resolve: { alias },
        test: {
          ...shared,
          name: "ui",
          environment: "jsdom",
          setupFiles: ["./tests/support/dom-polyfills.ts", "./tests/support/setup.ts"],
          include: ["tests/**/*.test.{ts,tsx}"],
          exclude: ["tests/checks/**"],
        },
      },
      {
        resolve: { alias },
        test: {
          ...shared,
          name: "checks",
          environment: "node",
          include: ["tests/checks/**/*.test.ts"],
        },
      },
    ],
  },
})
