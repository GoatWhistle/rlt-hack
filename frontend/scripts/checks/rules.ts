import { cssBreakpoints } from "./css-breakpoints.ts"
import { cssDuplicates } from "./css-duplicates.ts"
import { cssLiterals } from "./css-literals.ts"
import { cssModules } from "./css-modules.ts"
import { cssMonoWeight } from "./css-mono-weight.ts"
import { cssTransitions } from "./css-transitions.ts"
import { cyrillic } from "./cyrillic.ts"
import { fileLength } from "./file-length.ts"
import { jsxText } from "./jsx-text.ts"
import { noComments } from "./no-comments.ts"
import { packageSize } from "./package-size.ts"
import { packageSubject } from "./package-subject.ts"
import type { Rule, SourceFile, Violation } from "./source-files.ts"

export const RULES: readonly Rule[] = [
  fileLength,
  noComments,
  cyrillic,
  packageSize,
  packageSubject,
  cssLiterals,
  cssModules,
  cssDuplicates,
  cssBreakpoints,
  cssTransitions,
  cssMonoWeight,
  jsxText,
]

export function runRules(files: readonly SourceFile[]): Violation[] {
  if (files.length === 0) {
    return [
      {
        rule: "rules",
        path: ".",
        message: "no file was scanned, so a pass would prove nothing",
      },
    ]
  }
  return RULES.flatMap((rule) => rule.check(files))
}

export function formatReport(violations: readonly Violation[], scanned: number): string {
  if (violations.length === 0)
    return `rules: ${RULES.length} checks passed over ${scanned} files`
  return violations
    .map((violation) => `[${violation.rule}] ${violation.path}: ${violation.message}`)
    .join("\n")
}
