import type { SourceFile } from "../../scripts/checks/source-files.ts"

export function file(path: string, content: string): SourceFile {
  return { path, content }
}

export function lines(count: number, line = "export const value = 1"): string {
  return `${Array.from({ length: count }, () => line).join("\n")}\n`
}
