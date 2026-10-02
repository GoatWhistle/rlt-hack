import { hasExtension, lineOf, type Rule } from "./source-files.ts"

const DOTS = /[·•‧∙⋅・]/u
const SCANNED = [".ts", ".tsx", ".css", ".html", ".json"]

export const dotSeparators: Rule = {
  name: "dot-separators",
  check: (files) =>
    files
      .filter((file) => file.path.startsWith("src/"))
      .filter((file) => hasExtension(file.path, SCANNED))
      .flatMap((file) => {
        const offset = file.content.search(DOTS)
        if (offset === -1) return []
        return [
          {
            rule: "dot-separators",
            path: file.path,
            message: `dot separator on line ${lineOf(file.content, offset)}: lay facts out as separate items with a gap, a list or plain words`,
          },
        ]
      }),
}
