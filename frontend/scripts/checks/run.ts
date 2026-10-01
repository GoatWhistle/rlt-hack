import { fileURLToPath } from "node:url"
import { formatReport, runRules } from "./rules.ts"
import { readSources } from "./source-files.ts"

const root = fileURLToPath(new URL("../..", import.meta.url))
const files = readSources(root)
const violations = runRules(files)
const report = formatReport(violations, files.length)

if (violations.length > 0) {
  console.error(report)
  process.exit(1)
}
console.log(report)
