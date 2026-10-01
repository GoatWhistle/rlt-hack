import ts from "typescript"

export function parse(path: string, content: string): ts.SourceFile {
  const kind = path.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  return ts.createSourceFile(path, content, ts.ScriptTarget.Latest, true, kind)
}

export function walk(node: ts.Node, visit: (node: ts.Node) => void): void {
  visit(node)
  for (const child of node.getChildren()) walk(child, visit)
}

export type CommentRange = {
  readonly start: number
  readonly text: string
}

export function comments(source: ts.SourceFile): CommentRange[] {
  const text = source.getFullText()
  const seen = new Map<number, CommentRange>()
  const jsxText: [number, number][] = []
  const collect = (ranges: readonly ts.CommentRange[] | undefined) => {
    for (const range of ranges ?? []) {
      seen.set(range.pos, { start: range.pos, text: text.slice(range.pos, range.end) })
    }
  }
  walk(source, (node) => {
    if (ts.isJsxText(node)) {
      jsxText.push([node.getFullStart(), node.getEnd()])
      return
    }
    collect(ts.getLeadingCommentRanges(text, node.getFullStart()))
    collect(ts.getTrailingCommentRanges(text, node.getEnd()))
  })
  const insideJsxText = (offset: number) =>
    jsxText.some(([start, end]) => offset >= start && offset < end)
  return [...seen.values()]
    .filter((range) => !insideJsxText(range.start))
    .sort((left, right) => left.start - right.start)
}

export { ts }
