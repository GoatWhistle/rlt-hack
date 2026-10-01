import { stripCssComments } from "./css-syntax.ts"
import {
  hasExtension,
  lineOf,
  type Rule,
  type SourceFile,
  type Violation,
} from "./source-files.ts"

export const TOKENS_DIRECTORY = "src/shared/styles/tokens/"

type Literal = { readonly pattern: RegExp; readonly hint: string; readonly cssOnly: boolean }

const LITERALS: readonly Literal[] = [
  {
    pattern: /#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb|color)\(/,
    hint: "a literal colour",
    cssOnly: false,
  },
  { pattern: /(?<![\w.-])\d*\.?\d+m?s\b/, hint: "a literal duration", cssOnly: true },
  { pattern: /\b(?:cubic-bezier|steps)\(/, hint: "a literal easing", cssOnly: true },
  { pattern: /!important/, hint: "!important", cssOnly: true },
]

function scan(file: SourceFile): Violation[] {
  const isCss = file.path.endsWith(".css")
  const content = isCss ? stripCssComments(file.content) : file.content
  return LITERALS.filter((literal) => isCss || !literal.cssOnly).flatMap((literal) => {
    const match = literal.pattern.exec(content)
    if (!match) return []
    return [
      {
        rule: "css-literals",
        path: file.path,
        message: `${literal.hint} on line ${lineOf(content, match.index)}: use a token from ${TOKENS_DIRECTORY}`,
      },
    ]
  })
}

export const cssLiterals: Rule = {
  name: "css-literals",
  check: (files) =>
    files
      .filter((file) => file.path.startsWith("src/") && !file.path.startsWith(TOKENS_DIRECTORY))
      .filter((file) => hasExtension(file.path, [".css", ".tsx"]))
      .flatMap(scan),
}
