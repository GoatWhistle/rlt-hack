import { cssBlocks } from "./css-syntax.ts"
import { lineOf, type Rule, type SourceFile, type Violation } from "./source-files.ts"

const MONO = /^font-family\s*:\s*var\(--font-mono\)/
const WEIGHT = /^font-weight\s*:\s*(.+)$/
const HEAVY = /--weight-(?:semibold|bold)|^(?:[6-9]00|bold|bolder)$/

function heavy(declaration: string): boolean {
  const weight = WEIGHT.exec(declaration)?.[1]?.trim()
  return weight !== undefined && HEAVY.test(weight)
}

function scan(file: SourceFile): Violation[] {
  return cssBlocks(file.content).flatMap((block) => {
    const mono = block.declarations.some((declaration) => MONO.test(declaration))
    if (!mono || !block.declarations.some(heavy)) return []
    return [
      {
        rule: "css-mono-weight",
        path: file.path,
        message: `${block.prelude} on line ${lineOf(file.content, block.offset)} sets a monospace font heavier than 500: there is no such face, use --weight-medium`,
      },
    ]
  })
}

export const cssMonoWeight: Rule = {
  name: "css-mono-weight",
  check: (files) =>
    files
      .filter((file) => file.path.startsWith("src/") && file.path.endsWith(".css"))
      .flatMap(scan),
}
