import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"
import { formatReport, RULES, runRules } from "../../scripts/checks/rules.ts"
import {
  directoryOf,
  hasExtension,
  lineCount,
  lineOf,
  listPaths,
  readSources,
} from "../../scripts/checks/source-files.ts"
import { file } from "./fixtures.ts"

const root = fileURLToPath(new URL("../..", import.meta.url))

describe("the repository", () => {
  it("passes every rule", () => {
    const files = readSources(root)
    expect(files.length).toBeGreaterThan(50)
    expect(formatReport(runRules(files), files.length)).toBe(
      `rules: ${RULES.length} checks passed over ${files.length} files`,
    )
  })

  it("lists tracked and new files without dependencies or binaries", () => {
    const paths = listPaths(root)
    expect(paths).toContain("src/main.tsx")
    expect(paths.some((path) => path.includes("node_modules/"))).toBe(false)
    expect(paths).not.toContain("package-lock.json")
  })
})

describe("the rule runner", () => {
  it("fails when nothing was scanned", () => {
    expect(runRules([]).map((violation) => violation.rule)).toEqual(["rules"])
  })

  it("prints every violation with its rule", () => {
    const report = formatReport(runRules([file("src/a.ts", "// note\n")]), 1)
    expect(report).toBe(
      "[no-comments] src/a.ts: comment on line 1: move the explanation into docs",
    )
  })
})

describe("source helpers", () => {
  it("count lines with and without a trailing newline", () => {
    expect([lineCount(""), lineCount("a"), lineCount("a\n"), lineCount("a\nb")]).toEqual([
      0, 1, 1, 2,
    ])
  })

  it("locate offsets, directories and extensions", () => {
    expect(lineOf("a\nb\nc", 4)).toBe(3)
    expect([directoryOf("a/b/c.ts"), directoryOf("c.ts")]).toEqual(["a/b", "."])
    expect(hasExtension("a.tsx", [".ts", ".tsx"])).toBe(true)
  })
})
