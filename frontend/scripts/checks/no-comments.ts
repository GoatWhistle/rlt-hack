import {
  hasExtension,
  lineOf,
  type Rule,
  type SourceFile,
  type Violation,
} from "./source-files.ts"
import { comments, parse } from "./syntax-tree.ts"

const ALLOWED = /^\/\/ biome-ignore [\w/-]+: \S/
const CSS_COMMENT = /\/\*[\s\S]*?\*\//g
const HTML_COMMENT = /<!--[\s\S]*?-->/g

function violation(file: SourceFile, offset: number): Violation {
  return {
    rule: "no-comments",
    path: file.path,
    message: `comment on line ${lineOf(file.content, offset)}: move the explanation into docs`,
  }
}

function scriptComments(file: SourceFile): Violation[] {
  return comments(parse(file.path, file.content))
    .filter((comment) => !ALLOWED.test(comment.text))
    .map((comment) => violation(file, comment.start))
}

function patternComments(file: SourceFile, pattern: RegExp): Violation[] {
  return [...file.content.matchAll(pattern)].map((match) => violation(file, match.index))
}

function inspect(file: SourceFile): Violation[] {
  if (hasExtension(file.path, [".ts", ".tsx", ".mts"])) return scriptComments(file)
  if (file.path.endsWith(".css")) return patternComments(file, CSS_COMMENT)
  if (file.path.endsWith(".html")) return patternComments(file, HTML_COMMENT)
  return []
}

export const noComments: Rule = {
  name: "no-comments",
  check: (files) => files.flatMap(inspect),
}
