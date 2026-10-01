import { posix } from "node:path"
import { classNames } from "./css-syntax.ts"
import {
  directoryOf,
  hasExtension,
  type Rule,
  type SourceFile,
  type Violation,
} from "./source-files.ts"

export const MODULE_NAME = "styles.module.css"
export const GLOBAL_STYLES = "src/shared/styles/"
export const GLOBAL_ENTRY = "src/main.tsx"

const CSS_IMPORT = /import\s+(?:(\w+)\s+from\s+)?["']([^"']+\.css)["']/g
const PROPERTY = /(?<![\w./])styles\.([A-Za-z_]\w*)/g

function fail(path: string, message: string): Violation {
  return { rule: "css-modules", path, message }
}

function placement(sheet: SourceFile, paths: ReadonlySet<string>): Violation[] {
  if (sheet.path.startsWith(GLOBAL_STYLES)) return []
  if (!sheet.path.endsWith(`/${MODULE_NAME}`)) {
    return [
      fail(
        sheet.path,
        `a component sheet is named ${MODULE_NAME}, global sheets live in ${GLOBAL_STYLES}`,
      ),
    ]
  }
  const owner = `${directoryOf(sheet.path)}/index.tsx`
  return paths.has(owner)
    ? []
    : [fail(sheet.path, `the sheet needs its component ${owner} beside it`)]
}

function imports(script: SourceFile): Violation[] {
  return [...script.content.matchAll(CSS_IMPORT)].flatMap((match) => {
    const target = posix.normalize(posix.join(directoryOf(script.path), match[2] ?? ""))
    if (target.startsWith(GLOBAL_STYLES)) {
      return script.path === GLOBAL_ENTRY
        ? []
        : [fail(script.path, `global styles are imported only by ${GLOBAL_ENTRY}`)]
    }
    return directoryOf(target) === directoryOf(script.path)
      ? []
      : [fail(script.path, `imports a sheet of another component: ${target}`)]
  })
}

function usage(sheet: SourceFile, scripts: readonly SourceFile[]): Violation[] {
  const directory = directoryOf(sheet.path)
  const owners = scripts.filter((script) => directoryOf(script.path) === directory)
  if (owners.some((owner) => owner.content.includes("styles["))) {
    return [fail(sheet.path, "read classes as styles.name so unused ones can be found")]
  }
  const declared = new Set(classNames(sheet.content))
  const used = new Set(
    owners.flatMap((owner) =>
      [...owner.content.matchAll(PROPERTY)].map((match) => match[1] ?? ""),
    ),
  )
  const unused = [...declared].filter((name) => !used.has(name))
  const missing = [...used].filter((name) => !declared.has(name))
  return [
    ...unused.map((name) => fail(sheet.path, `class .${name} is never read`)),
    ...missing.map((name) => fail(sheet.path, `styles.${name} is read but never declared`)),
  ]
}

export const cssModules: Rule = {
  name: "css-modules",
  check: (files) => {
    const source = files.filter((file) => file.path.startsWith("src/"))
    const paths = new Set(source.map((file) => file.path))
    const sheets = source.filter((file) => file.path.endsWith(".css"))
    const scripts = source.filter((file) => hasExtension(file.path, [".ts", ".tsx"]))
    const modules = sheets.filter((sheet) => sheet.path.endsWith(`/${MODULE_NAME}`))
    return [
      ...sheets.flatMap((sheet) => placement(sheet, paths)),
      ...scripts.flatMap(imports),
      ...modules.flatMap((sheet) => usage(sheet, scripts)),
    ]
  },
}
