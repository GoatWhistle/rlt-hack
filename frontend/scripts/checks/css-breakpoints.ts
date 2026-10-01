import { stripCssComments } from "./css-syntax.ts"
import {
  hasExtension,
  lineOf,
  type Rule,
  type SourceFile,
  type Violation,
} from "./source-files.ts"

export const BREAKPOINTS = ["30rem", "48rem", "64rem", "75rem", "100rem"] as const

const LOWER_BOUNDS = new Set<string>(BREAKPOINTS)
const UPPER_BOUNDS = new Set(
  BREAKPOINTS.map((value) => `${(Number.parseFloat(value) - 0.01).toFixed(2)}rem`),
)
const WIDTH_QUERY = /\((min|max)-width:\s*([^)]+)\)/g
const MEDIA_PRELUDE = /@media[^{]*/g

type Query = { readonly text: string; readonly offset: number }

function queriesOf(file: SourceFile): Query[] {
  if (!file.path.endsWith(".css")) return [{ text: file.content, offset: 0 }]
  const content = stripCssComments(file.content)
  return [...content.matchAll(MEDIA_PRELUDE)].map((match) => ({
    text: match[0],
    offset: match.index,
  }))
}

function scan(file: SourceFile): Violation[] {
  return queriesOf(file).flatMap((query) =>
    [...query.text.matchAll(WIDTH_QUERY)].flatMap((match) => {
      const [whole, bound, raw = ""] = match
      const allowed = bound === "min" ? LOWER_BOUNDS : UPPER_BOUNDS
      if (allowed.has(raw.trim())) return []
      const line = lineOf(file.content, query.offset + match.index)
      return [
        {
          rule: "css-breakpoints",
          path: file.path,
          message: `${whole} on line ${line}: use one of ${[...allowed].join(", ")}`,
        },
      ]
    }),
  )
}

export const cssBreakpoints: Rule = {
  name: "css-breakpoints",
  check: (files) =>
    files
      .filter((file) => file.path.startsWith("src/"))
      .filter((file) => hasExtension(file.path, [".css", ".ts", ".tsx"]))
      .flatMap(scan),
}
