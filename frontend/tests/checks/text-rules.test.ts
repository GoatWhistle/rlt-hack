import { describe, expect, it } from "vitest"
import { cyrillic } from "../../scripts/checks/cyrillic.ts"
import { FILE_LINE_LIMIT, fileLength } from "../../scripts/checks/file-length.ts"
import { jsxText } from "../../scripts/checks/jsx-text.ts"
import { noComments } from "../../scripts/checks/no-comments.ts"
import { file, lines } from "./fixtures.ts"

describe("file length", () => {
  it("rejects a source file over the limit", () => {
    const found = fileLength.check([file("src/big.ts", lines(FILE_LINE_LIMIT + 1))])
    expect(found.map((violation) => violation.path)).toEqual(["src/big.ts"])
  })

  it("accepts a file exactly at the limit and ignores unmeasured types", () => {
    expect(
      fileLength.check([
        file("src/edge.ts", lines(FILE_LINE_LIMIT)),
        file("README.md", lines(FILE_LINE_LIMIT * 2)),
      ]),
    ).toEqual([])
  })
})

describe("no comments", () => {
  it("finds line, block and doc comments in scripts", () => {
    const source = "// line\nconst a = 1 /* block */\n/** doc */\nexport { a }\n"
    expect(noComments.check([file("src/a.ts", source)])).toHaveLength(3)
  })

  it("finds a comment before a closing brace and inside jsx braces", () => {
    const source = "export function A() {\n  return <div>{/* hidden */}</div>\n  // tail\n}\n"
    expect(noComments.check([file("src/a.tsx", source)])).toHaveLength(2)
  })

  it("does not mistake jsx text, strings or urls for comments", () => {
    const source =
      'export const A = () => <a href="https://x.dev">// not a comment</a>\nconst u = "//x"\n'
    expect(noComments.check([file("src/a.tsx", source)])).toEqual([])
  })

  it("allows only a biome-ignore with a reason", () => {
    const allowed =
      "// biome-ignore lint/style/noDefaultExport: the tool reads the default\nexport default 1\n"
    const bare = "// biome-ignore lint/style/noDefaultExport\nexport default 1\n"
    expect(noComments.check([file("a.config.ts", allowed)])).toEqual([])
    expect(noComments.check([file("b.config.ts", bare)])).toHaveLength(1)
  })

  it("finds comments in stylesheets and html", () => {
    const found = noComments.check([
      file("src/a/styles.module.css", ".a { color: red; } /* why */\n"),
      file("index.html", "<!-- note --><div></div>\n"),
      file("data.json", '{ "a": "/* text */" }\n'),
    ])
    expect(found.map((violation) => violation.path)).toEqual([
      "src/a/styles.module.css",
      "index.html",
    ])
  })
})

describe("cyrillic", () => {
  it("rejects russian text in code outside the dictionaries", () => {
    const found = cyrillic.check([
      file("src/pages/home/index.tsx", 'const title = "Привет"\n'),
      file("scripts/checks/x.ts", 'const a = "ё"\n'),
    ])
    expect(found).toHaveLength(2)
  })

  it("accepts dictionaries, tests and ascii code", () => {
    expect(
      cyrillic.check([
        file("src/shared/i18n/locales/ru/common.json", '{ "a": "Привет" }'),
        file("src/shared/i18n/locales/ru/x.ts", 'const a = "Привет"'),
        file("tests/x.test.ts", 'expect("Привет")'),
        file("src/a.ts", "const a = 1"),
      ]),
    ).toEqual([])
  })
})

describe("jsx text", () => {
  it("rejects literal text and literal accessible names", () => {
    const source = 'export const A = () => <button aria-label="Close">Save</button>\n'
    expect(jsxText.check([file("src/a.tsx", source)])).toHaveLength(2)
  })

  it("accepts translated text, symbols and non-text attributes", () => {
    const source =
      'export const A = () => <a className="x" aria-label={t("a")} title={t("b")}>{t("c")} × 42</a>\n'
    expect(jsxText.check([file("src/a.tsx", source)])).toEqual([])
  })

  it("ignores tests and plain modules", () => {
    expect(
      jsxText.check([
        file("tests/a.test.tsx", "render(<p>Hello</p>)"),
        file("src/a.ts", 'const a = "Hello"'),
      ]),
    ).toEqual([])
  })
})
