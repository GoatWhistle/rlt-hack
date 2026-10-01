import { directoryOf, type Rule } from "./source-files.ts"

const BANNED = new Set(["utils", "util", "helpers", "common", "misc", "lib", "core", "shared"])
const ALLOWED = new Set(["src/shared", "tests/shared"])

function ancestors(directory: string): string[] {
  const parts = directory.split("/")
  return parts.map((_, index) => parts.slice(0, index + 1).join("/"))
}

export const packageSubject: Rule = {
  name: "package-subject",
  check: (files) => {
    const directories = new Set(
      files
        .filter((file) => file.path.startsWith("src/") || file.path.startsWith("tests/"))
        .flatMap((file) => ancestors(directoryOf(file.path))),
    )
    return [...directories]
      .sort()
      .filter((directory) => !ALLOWED.has(directory))
      .filter((directory) => BANNED.has(directory.slice(directory.lastIndexOf("/") + 1)))
      .map((directory) => ({
        rule: "package-subject",
        path: directory,
        message: "a package is named by what it holds, not by the fact of reuse",
      }))
  },
}
