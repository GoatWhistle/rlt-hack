import { directoryOf, hasExtension, type Rule } from "./source-files.ts"

export const SOURCE_LIMIT = 20
export const TEST_LIMIT = 30

const COUNTED = [".ts", ".tsx"]
const TREES = ["src/", "scripts/", "tests/", "e2e/"]

function limitFor(directory: string): number {
  return directory.startsWith("tests/") || directory.startsWith("e2e")
    ? TEST_LIMIT
    : SOURCE_LIMIT
}

export const packageSize: Rule = {
  name: "package-size",
  check: (files) => {
    const counts = new Map<string, number>()
    for (const file of files) {
      if (!TREES.some((tree) => file.path.startsWith(tree))) continue
      if (!hasExtension(file.path, COUNTED) || file.path.endsWith(".d.ts")) continue
      const directory = directoryOf(file.path)
      counts.set(directory, (counts.get(directory) ?? 0) + 1)
    }
    return [...counts]
      .filter(([directory, count]) => count > limitFor(directory))
      .map(([directory, count]) => ({
        rule: "package-size",
        path: directory,
        message: `${count} files, the limit is ${limitFor(directory)}: cut the package by subject`,
      }))
  },
}
