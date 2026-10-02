import { describe, expect, it } from "vitest"
import { cssBreakpoints } from "../../scripts/checks/css-breakpoints.ts"
import { cssDuplicates } from "../../scripts/checks/css-duplicates.ts"
import { cssLiterals } from "../../scripts/checks/css-literals.ts"
import { cssModules } from "../../scripts/checks/css-modules.ts"
import { cssMonoWeight } from "../../scripts/checks/css-mono-weight.ts"
import { classNames, cssBlocks } from "../../scripts/checks/css-syntax.ts"
import { cssTransitions } from "../../scripts/checks/css-transitions.ts"
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

  it("rejects literal border widths but accepts width tokens", () => {
    const sheet = file(
      "src/a/styles.module.css",
      ".a { border: 1.5px dashed var(--x); }\n.b { border-block-start: var(--line-width) solid var(--x); }",
    )
    expect(cssLiterals.check([sheet]).map((violation) => violation.message)).toEqual([
      "a literal border width on line 1: use a token from src/shared/styles/tokens/",
    ])
    expect(
      cssLiterals.check([
        file("src/b/styles.module.css", ".b { border-radius: var(--radius-md); gap: 1px; }"),
      ]),
    ).toEqual([])
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

describe("css breakpoints", () => {
  it("rejects widths outside the shared set in sheets and scripts", () => {
    const found = cssBreakpoints.check([
      file("src/a/styles.module.css", "@media (max-width: 48rem) { .a { gap: 0; } }"),
      file("src/b/styles.module.css", "@media (min-width: 60rem) { .b { gap: 0; } }"),
      file("src/c/view.ts", 'export const NARROW = "(max-width: 600px)"'),
    ])
    expect(found.map((violation) => violation.path)).toEqual([
      "src/a/styles.module.css",
      "src/b/styles.module.css",
      "src/c/view.ts",
    ])
    expect(found[0]?.message).toContain("47.99rem")
  })

  it("accepts the shared lower and upper bounds", () => {
    expect(
      cssBreakpoints.check([
        file(
          "src/a/styles.module.css",
          "@media (min-width: 75rem) and (hover: hover) { .a { gap: 0; } }\n@media (max-width: 29.99rem) { .a { gap: 1px; } }",
        ),
        file("src/b/view.ts", 'export const NARROW = "(max-width: 63.99rem)"'),
        file("src/c/styles.module.css", ".c { max-width: 60rem; }"),
      ]),
    ).toEqual([])
  })
})

describe("css transitions", () => {
  it("rejects transitions of layout sizes, including transition tokens", () => {
    const found = cssTransitions.check([
      file("src/a/styles.module.css", ".a { transition: inline-size var(--dur); }"),
      file(
        "src/shared/styles/tokens/motion.css",
        ":root { --transition-x: opacity 1ms, height 1ms; }",
      ),
    ])
    expect(found.map((violation) => violation.message)).toEqual([
      ".a on line 1 animates inline-size: animate transform or opacity instead",
      ":root on line 1 animates height: animate transform or opacity instead",
    ])
  })

  it("accepts transform, opacity and size tokens inside values", () => {
    expect(
      cssTransitions.check([
        file(
          "src/a/styles.module.css",
          ".a { transition: transform var(--dur), opacity var(--dur); width: var(--indicator-width); }",
        ),
      ]),
    ).toEqual([])
  })
})

describe("css mono weight", () => {
  it("rejects a monospace font heavier than the faces that exist", () => {
    const sheet = file(
      "src/a/styles.module.css",
      ".a { font-family: var(--font-mono); font-weight: var(--weight-semibold); }\n.b { font-family: var(--font-mono); font-weight: 700; }",
    )
    expect(cssMonoWeight.check([sheet]).map((violation) => violation.message)).toEqual([
      expect.stringContaining(".a on line 1"),
      expect.stringContaining(".b on line 2"),
    ])
  })

  it("accepts medium monospace and heavy text in other fonts", () => {
    const sheet = file(
      "src/a/styles.module.css",
      ".a { font-family: var(--font-mono); font-weight: var(--weight-medium); }\n.b { font-weight: var(--weight-bold); }",
    )
    expect(cssMonoWeight.check([sheet])).toEqual([])
  })
})
