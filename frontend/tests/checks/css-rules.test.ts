import { describe, expect, it } from "vitest"
import { cssDuplicates } from "../../scripts/checks/css-duplicates.ts"
import { cssLiterals } from "../../scripts/checks/css-literals.ts"
import { cssModules } from "../../scripts/checks/css-modules.ts"
import { classNames, cssBlocks } from "../../scripts/checks/css-syntax.ts"
import { file } from "./fixtures.ts"

const SHEET = "src/shared/ui/card/styles.module.css"
const OWNER = "src/shared/ui/card/index.tsx"
const OWNER_SOURCE = 'import styles from "./styles.module.css"\nstyles.card\nstyles.title\n'

describe("css syntax", () => {
  it("reads leaf blocks inside at-rules and skips imports and comments", () => {
    const blocks = cssBlocks(
      '@import "./a.css";\n/* .ghost {} */\n.a { color: x; }\n@media (x) { .b:hover { gap: 1px; } }',
    )
    expect(blocks.map((block) => block.prelude)).toEqual([".a", ".b:hover"])
    expect(blocks[1]?.declarations).toEqual(["gap: 1px"])
  })

  it("collects class names from selectors only", () => {
    expect(
      classNames(".a .b, .c[data-x] { background: url(./x.png); width: 0.5rem; }"),
    ).toEqual(["a", "b", "c"])
  })
})

describe("css literals", () => {
  it("rejects colours, durations, easings and !important outside tokens", () => {
    const sheet = file(
      "src/a/styles.module.css",
      ".a { color: #fff; transition: color 200ms cubic-bezier(0, 0, 1, 1); width: 1px !important; }",
    )
    const inline = file("src/a/index.tsx", 'const s = { color: "rgb(0 0 0)" }')
    expect(cssLiterals.check([sheet, inline])).toHaveLength(5)
  })

  it("accepts tokens, token files and durations in scripts", () => {
    expect(
      cssLiterals.check([
        file("src/a/styles.module.css", ".a { color: var(--text); width: 2.5rem; }"),
        file("src/shared/styles/tokens/color.css", ":root { --x: #fff; --d: 1ms; }"),
        file("src/a/index.tsx", "setTimeout(run, 300)"),
      ]),
    ).toEqual([])
  })
})

describe("css modules", () => {
  it("accepts a colocated sheet whose classes are all read", () => {
    const sheet = file(SHEET, ".card { gap: 1px; }\n.title { gap: 2px; }")
    expect(cssModules.check([sheet, file(OWNER, OWNER_SOURCE)])).toEqual([])
  })

  it("rejects unused and undeclared classes", () => {
    const sheet = file(SHEET, ".card { gap: 1px; }\n.unused { gap: 2px; }")
    const messages = cssModules.check([sheet, file(OWNER, OWNER_SOURCE)]).map((v) => v.message)
    expect(messages).toEqual([
      "class .unused is never read",
      "styles.title is read but never declared",
    ])
  })

  it("rejects dynamic class access", () => {
    const owner = file(OWNER, 'import styles from "./styles.module.css"\nstyles[name]')
    expect(cssModules.check([file(SHEET, ".card {}"), owner])).toHaveLength(1)
  })

  it("rejects misplaced, orphan and borrowed sheets", () => {
    const found = cssModules.check([
      file("src/a/button.css", ".a {}"),
      file("src/orphan/styles.module.css", ".a {}"),
      file(SHEET, ".card {}\n.title {}"),
      file(OWNER, OWNER_SOURCE),
      file("src/other/index.tsx", 'import x from "../shared/ui/card/styles.module.css"'),
      file("src/other/view.tsx", 'import "../shared/styles/global.css"'),
    ])
    expect(found.map((violation) => violation.path)).toEqual([
      "src/a/button.css",
      "src/orphan/styles.module.css",
      "src/other/index.tsx",
      "src/other/view.tsx",
      "src/orphan/styles.module.css",
    ])
  })

  it("lets only the entry point import global styles", () => {
    const entry = file("src/main.tsx", 'import "./shared/styles/global.css"')
    expect(cssModules.check([entry, file("src/shared/styles/global.css", "body {}")])).toEqual(
      [],
    )
  })
})

describe("css duplicates", () => {
  const block = "display: flex; gap: var(--space-2); align-items: center;"

  it("rejects the same declaration block in two sheets, in any order", () => {
    const found = cssDuplicates.check([
      file("src/a/styles.module.css", `.a { ${block} }`),
      file(
        "src/b/styles.module.css",
        ".b { align-items: center; gap: var(--space-2); display: flex; }",
      ),
    ])
    expect(found).toHaveLength(1)
    expect(found[0]?.message).toContain("src/a/styles.module.css:1")
  })

  it("accepts short blocks, keyframes and token files", () => {
    expect(
      cssDuplicates.check([
        file(
          "src/a/styles.module.css",
          ".a { gap: 1px; color: x; }\n.b { gap: 1px; color: x; }",
        ),
        file("src/shared/styles/tokens/a.css", `:root { ${block} }`),
        file("src/shared/styles/tokens/b.css", `:root { ${block} }`),
        file("src/c/styles.module.css", `@font-face { ${block} }\n@font-face { ${block} }`),
      ]),
    ).toEqual([])
  })
})
