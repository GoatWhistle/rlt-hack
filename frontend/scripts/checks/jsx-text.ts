import { lineOf, type Rule, type SourceFile, type Violation } from "./source-files.ts"
import { parse, ts, walk } from "./syntax-tree.ts"

export const TEXT_ATTRIBUTES = new Set([
  "aria-label",
  "aria-description",
  "title",
  "alt",
  "placeholder",
])

const LETTER = /\p{L}/u

function literalAttribute(node: ts.Node): boolean {
  if (!ts.isJsxAttribute(node) || !node.initializer) return false
  const name = node.name.getText()
  return TEXT_ATTRIBUTES.has(name) && ts.isStringLiteral(node.initializer)
}

function inspect(file: SourceFile): Violation[] {
  const found: Violation[] = []
  walk(parse(file.path, file.content), (node) => {
    const text = ts.isJsxText(node) && LETTER.test(node.getText())
    const attribute = literalAttribute(node) && LETTER.test(node.getText())
    if (!text && !attribute) return
    found.push({
      rule: "jsx-text",
      path: file.path,
      message: `user-facing text on line ${lineOf(file.content, node.getStart())}: take it from the dictionary with t()`,
    })
  })
  return found
}

export const jsxText: Rule = {
  name: "jsx-text",
  check: (files) =>
    files
      .filter((file) => file.path.startsWith("src/") && file.path.endsWith(".tsx"))
      .flatMap(inspect),
}
