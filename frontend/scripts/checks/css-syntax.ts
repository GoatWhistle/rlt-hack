export type CssBlock = {
  readonly prelude: string
  readonly declarations: readonly string[]
  readonly offset: number
}

type OpenBlock = { prelude: string; start: number; nested: boolean }

const COMMENT = /\/\*[\s\S]*?\*\//g
const CLASS_NAME = /\.(-?[_a-zA-Z][\w-]*)/g

export function stripCssComments(content: string): string {
  return content.replace(COMMENT, (comment) => " ".repeat(comment.length))
}

function declarationsOf(body: string): string[] {
  return body
    .split(";")
    .map((declaration) => declaration.replace(/\s+/g, " ").trim())
    .filter((declaration) => declaration.length > 0)
}

export function cssBlocks(content: string): CssBlock[] {
  const source = stripCssComments(content)
  const blocks: CssBlock[] = []
  const stack: OpenBlock[] = []
  let segmentStart = 0

  const open = (index: number) => {
    const parent = stack.at(-1)
    if (parent) parent.nested = true
    stack.push({
      prelude: source.slice(segmentStart, index).trim(),
      start: index,
      nested: false,
    })
  }

  const close = (index: number) => {
    const block = stack.pop()
    if (!block || block.nested) return
    blocks.push({
      prelude: block.prelude,
      declarations: declarationsOf(source.slice(block.start + 1, index)),
      offset: block.start,
    })
  }

  for (let index = 0; index < source.length; index++) {
    const char = source[index]
    if (char === "{") open(index)
    else if (char === "}") close(index)
    else if (char !== ";" || (stack.length > 0 && !stack.at(-1)?.nested)) continue
    segmentStart = index + 1
  }
  return blocks
}

export function classNames(content: string): string[] {
  const names = cssBlocks(content)
    .filter((block) => !block.prelude.startsWith("@"))
    .flatMap((block) => [...block.prelude.matchAll(CLASS_NAME)].map((match) => match[1] ?? ""))
  return [...new Set(names)].filter((name) => name.length > 0)
}
