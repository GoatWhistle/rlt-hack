import { TOKENS_DIRECTORY } from "./css-literals.ts"
import { cssBlocks } from "./css-syntax.ts"
import { lineOf, type Rule } from "./source-files.ts"

export const MIN_DECLARATIONS = 3

type Location = { readonly path: string; readonly line: number; readonly prelude: string }

function signature(declarations: readonly string[]): string {
  return [...declarations].sort().join(";")
}

export const cssDuplicates: Rule = {
  name: "css-duplicates",
  check: (files) => {
    const seen = new Map<string, Location>()
    const found: [Location, Location][] = []
    const sheets = files.filter(
      (file) =>
        file.path.startsWith("src/") &&
        file.path.endsWith(".css") &&
        !file.path.startsWith(TOKENS_DIRECTORY),
    )
    for (const sheet of sheets) {
      for (const block of cssBlocks(sheet.content)) {
        if (block.prelude.startsWith("@") || block.declarations.length < MIN_DECLARATIONS)
          continue
        const key = signature(block.declarations)
        const here = {
          path: sheet.path,
          line: lineOf(sheet.content, block.offset),
          prelude: block.prelude,
        }
        const first = seen.get(key)
        if (first) found.push([first, here])
        else seen.set(key, here)
      }
    }
    return found.map(([first, second]) => ({
      rule: "css-duplicates",
      path: second.path,
      message: `${second.prelude} on line ${second.line} repeats ${first.prelude} in ${first.path}:${first.line}: reuse a component or extract a token`,
    }))
  },
}
