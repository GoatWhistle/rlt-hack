import { hasExtension, lineCount, type Rule } from "./source-files.ts"

export const FILE_LINE_LIMIT = 250

const MEASURED = [".ts", ".tsx", ".css", ".json", ".html", ".mjs"]

export const fileLength: Rule = {
  name: "file-length",
  check: (files) =>
    files
      .filter((file) => hasExtension(file.path, MEASURED))
      .map((file) => ({ file, lines: lineCount(file.content) }))
      .filter(({ lines }) => lines > FILE_LINE_LIMIT)
      .map(({ file, lines }) => ({
        rule: "file-length",
        path: file.path,
        message: `${lines} lines, the limit is ${FILE_LINE_LIMIT}: split the file by subject`,
      })),
}
