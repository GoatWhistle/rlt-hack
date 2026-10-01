import { hasExtension, lineOf, type Rule } from "./source-files.ts"

export const LOCALES_DIRECTORY = "src/shared/i18n/locales/"

const CYRILLIC = /\p{Script=Cyrillic}/u
const SCANNED = [".ts", ".tsx", ".css", ".html"]

export const cyrillic: Rule = {
  name: "cyrillic",
  check: (files) =>
    files
      .filter((file) => file.path.startsWith("src/") || file.path.startsWith("scripts/"))
      .filter((file) => hasExtension(file.path, SCANNED))
      .filter((file) => !file.path.startsWith(LOCALES_DIRECTORY))
      .flatMap((file) => {
        const offset = file.content.search(CYRILLIC)
        if (offset === -1) return []
        return [
          {
            rule: "cyrillic",
            path: file.path,
            message: `cyrillic on line ${lineOf(file.content, offset)}: product text lives in ${LOCALES_DIRECTORY}`,
          },
        ]
      }),
}
