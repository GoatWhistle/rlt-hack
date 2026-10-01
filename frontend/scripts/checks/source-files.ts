import { execFileSync } from "node:child_process"
import { readFileSync } from "node:fs"
import { join } from "node:path"

export type SourceFile = {
  readonly path: string
  readonly content: string
}

export type Violation = {
  readonly rule: string
  readonly path: string
  readonly message: string
}

export type Rule = {
  readonly name: string
  readonly check: (files: readonly SourceFile[]) => Violation[]
}

const SKIPPED = /(^|\/)(package-lock\.json|node_modules\/)/
const BINARY = /\.(png|jpe?g|gif|ico|webp|avif|woff2?|ttf|pdf|zip)$/

export function listPaths(root: string): string[] {
  const output = execFileSync(
    "git",
    ["ls-files", "--cached", "--others", "--exclude-standard", "--", "."],
    { cwd: root, encoding: "utf8" },
  )
  return [...new Set(output.split("\n"))]
    .filter((path) => path.length > 0)
    .filter((path) => !SKIPPED.test(path) && !BINARY.test(path))
    .sort()
}

export function readSources(root: string): SourceFile[] {
  return listPaths(root).flatMap((path) => {
    try {
      return [{ path, content: readFileSync(join(root, path), "utf8") }]
    } catch {
      return []
    }
  })
}

export function lineCount(content: string): number {
  if (content.length === 0) return 0
  const lines = content.split("\n").length
  return content.endsWith("\n") ? lines - 1 : lines
}

export function lineOf(content: string, offset: number): number {
  return content.slice(0, offset).split("\n").length
}

export function directoryOf(path: string): string {
  const slash = path.lastIndexOf("/")
  return slash === -1 ? "." : path.slice(0, slash)
}

export function hasExtension(path: string, extensions: readonly string[]): boolean {
  return extensions.some((extension) => path.endsWith(extension))
}
