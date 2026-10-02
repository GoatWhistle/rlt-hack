import { readdirSync, readFileSync } from "node:fs"
import { join, resolve } from "node:path"
import { leaves, type Tree } from "@tests/support/dictionaries"
import { describe, expect, it } from "vitest"
import { LOCALE_TAGS, LOCALES, type Locale } from "@/shared/i18n/locale"
import { NAMESPACES, resources } from "@/shared/i18n/resources"

const ROOT = resolve(process.cwd(), "src")
const LOCALES_ROOT = join(ROOT, "shared", "i18n", "locales")
const PLURAL = /_(zero|one|two|few|many|other)$/
const CALL = /\bt\(\s*["'`]([^"'`$]+)["'`]/g
const NAMESPACE = /useTranslation\(\s*["']([a-z]+)["']\s*\)/
const PARAM = /\{\{\s*([a-zA-Z]+)\s*(?:,\s*([a-zA-Z]+)\s*)?\}\}/g
const CYRILLIC = /\p{Script=Cyrillic}/u
const NUMERIC_PARAMS = new Set([
  "count",
  "total",
  "processed",
  "from",
  "to",
  "page",
  "pages",
  "index",
  "matched",
  "wins",
  "limit",
  "hits",
  "stock",
  "catalog",
  "inferred",
])
const TEXT_PARAMS = new Set([
  "category",
  "code",
  "columns",
  "date",
  "file",
  "filter",
  "found",
  "id",
  "inn",
  "name",
  "names",
  "price",
  "query",
  "row",
  "set",
  "text",
  "title",
  "unit",
  "value",
  "values",
])
const CYRILLIC_ALLOWED_IN_EN = new Set(["common:language.ru"])

function messages(locale: Locale) {
  return NAMESPACES.flatMap((namespace) =>
    leaves(resources[locale][namespace] as Tree).map(([path, value]) => ({
      id: `${namespace}:${path}`,
      value,
    })),
  )
}

function params(value: string) {
  return [...value.matchAll(PARAM)].map((match) => ({
    name: match[1] ?? "",
    format: match[2],
  }))
}

function wellFormatted(name: string, format: string | undefined): boolean {
  if (NUMERIC_PARAMS.has(name)) return format === "number"
  return TEXT_PARAMS.has(name) && format === undefined
}

function pluralFamilies(locale: Locale): Map<string, string[]> {
  const families = new Map<string, string[]>()
  for (const { id } of messages(locale)) {
    const form = PLURAL.exec(id)?.[1]
    if (!form) continue
    const base = id.replace(PLURAL, "")
    families.set(base, [...(families.get(base) ?? []), form])
  }
  return families
}

function keys(locale: (typeof LOCALES)[number], namespace: (typeof NAMESPACES)[number]) {
  return [
    ...new Set(
      leaves(resources[locale][namespace] as Tree).map(([path]) => path.replace(PLURAL, "")),
    ),
  ].sort()
}

function sources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = join(directory, entry.name)
    if (entry.isDirectory()) return sources(full)
    return /\.tsx?$/.test(entry.name) ? [full] : []
  })
}

function resolves(namespace: string, key: string): boolean {
  const tree = (resources.en as Record<string, Tree | undefined>)[namespace]
  return ["", "_one", "_other"].some((suffix) => {
    const node = `${key}${suffix}`
      .split(".")
      .reduce<string | Tree | undefined>(
        (acc, part) => (acc && typeof acc === "object" ? acc[part] : undefined),
        tree,
      )
    return typeof node === "string"
  })
}

type Reference = { readonly namespace: string; readonly key: string; readonly path: string }

function referencesIn(path: string): Reference[] {
  const content = readFileSync(path, "utf8")
  const fallback = NAMESPACE.exec(content)?.[1] ?? "common"
  return [...content.matchAll(CALL)].map((match) => {
    const literal = match[1] ?? ""
    const [namespace, key] = literal.includes(":") ? literal.split(":") : [fallback, literal]
    return { namespace: namespace ?? "", key: key ?? "", path }
  })
}

function referencedKeys(): Reference[] {
  return sources(ROOT).flatMap(referencesIn)
}

describe("dictionaries", () => {
  it("cover the same keys in every language", () => {
    for (const namespace of NAMESPACES) {
      expect(keys("ru", namespace), namespace).toEqual(keys("en", namespace))
    }
  })

  it("leave no message empty", () => {
    for (const locale of LOCALES) {
      for (const namespace of NAMESPACES) {
        for (const [path, value] of leaves(resources[locale][namespace] as Tree)) {
          expect(value.trim(), `${locale}/${namespace}:${path}`).not.toBe("")
        }
      }
    }
  })

  it("declare every file on disk, split the same way in every language", () => {
    for (const locale of LOCALES) {
      const files = readdirSync(join(LOCALES_ROOT, locale)).map((name) =>
        name.replace(/\.json$/, ""),
      )
      expect(files.sort(), locale).toEqual([...NAMESPACES].sort())
    }
  })

  it("keep every file under 250 lines", () => {
    for (const locale of LOCALES) {
      for (const namespace of NAMESPACES) {
        const content = readFileSync(join(LOCALES_ROOT, locale, `${namespace}.json`), "utf8")
        expect(content.split("\n").length, `${locale}/${namespace}`).toBeLessThanOrEqual(250)
      }
    }
  })

  it("resolve every literal key the code asks for", () => {
    const requested = referencedKeys()
    expect(requested.length).toBeGreaterThan(15)
    const missing = requested.filter(({ namespace, key }) => !resolves(namespace, key))
    expect(missing).toEqual([])
  })

  it("give every plural family exactly the forms its language needs", () => {
    for (const locale of LOCALES) {
      const needed = [
        ...new Intl.PluralRules(LOCALE_TAGS[locale]).resolvedOptions().pluralCategories,
      ]
      for (const [base, forms] of pluralFamilies(locale)) {
        expect(forms.sort(), `${locale}/${base}`).toEqual([...needed].sort())
      }
    }
    expect(pluralFamilies("ru").size).toBeGreaterThan(10)
  })

  it("show the count in every Russian plural form, since one also covers 21, 31…", () => {
    const blind = messages("ru").filter(
      ({ id, value }) => PLURAL.test(id) && !params(value).some((p) => p.name === "count"),
    )
    expect(blind.map(({ id }) => id)).toEqual([])
  })

  it("keep Cyrillic out of English copy", () => {
    const leaked = messages("en").filter(
      ({ id, value }) => CYRILLIC.test(value) && !CYRILLIC_ALLOWED_IN_EN.has(id),
    )
    expect(leaked.map(({ id }) => id)).toEqual([])
  })

  it("format every numeric parameter for the language and classify every parameter", () => {
    const misused = LOCALES.flatMap((locale) =>
      messages(locale).flatMap(({ id, value }) =>
        params(value)
          .filter(({ name, format }) => !wellFormatted(name, format))
          .map(
            ({ name, format }) => `${locale}/${id}: {{${name}${format ? `, ${format}` : ""}}}`,
          ),
      ),
    )
    expect(misused).toEqual([])
  })

  it("interpolate the same parameters in every language", () => {
    const names = (locale: Locale) =>
      new Map(
        messages(locale).map(({ id, value }) => [
          id.replace(PLURAL, ""),
          new Set(params(value).map((p) => p.name)),
        ]),
      )
    const ru = names("ru")
    for (const [id, used] of names("en")) {
      for (const name of used) expect(ru.get(id)?.has(name), `${id}: ${name}`).toBe(true)
    }
  })
})
