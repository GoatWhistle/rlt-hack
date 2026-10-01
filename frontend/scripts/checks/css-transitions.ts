import { cssBlocks } from "./css-syntax.ts"
import { lineOf, type Rule, type SourceFile, type Violation } from "./source-files.ts"

const TRANSITION_PROPERTY = /^(?:transition(?:-property)?|--transition[\w-]*)$/
const LAYOUT_PROPERTY = /(?:^|[\s,])((?:min-|max-)?(?:width|height|inline-size|block-size))\b/

function scan(file: SourceFile): Violation[] {
  return cssBlocks(file.content).flatMap((block) =>
    block.declarations.flatMap((declaration) => {
      const colon = declaration.indexOf(":")
      if (colon === -1 || !TRANSITION_PROPERTY.test(declaration.slice(0, colon).trim()))
        return []
      const animated = LAYOUT_PROPERTY.exec(declaration.slice(colon + 1))
      if (!animated) return []
      return [
        {
          rule: "css-transitions",
          path: file.path,
          message: `${block.prelude} on line ${lineOf(file.content, block.offset)} animates ${animated[1]}: animate transform or opacity instead`,
        },
      ]
    }),
  )
}

export const cssTransitions: Rule = {
  name: "css-transitions",
  check: (files) =>
    files
      .filter((file) => file.path.startsWith("src/") && file.path.endsWith(".css"))
      .flatMap(scan),
}
