import { readdirSync, readFileSync } from "node:fs"
import { join, resolve } from "node:path"
import { leaves, type Tree } from "@tests/support/dictionaries"
import { describe, expect, it } from "vitest"
import { LOCALES } from "@/shared/i18n/locale"
import { NAMESPACES, resources } from "@/shared/i18n/resources"

const ROOT = resolve(process.cwd(), "src")
const LOCALES_ROOT = join(ROOT, "shared", "i18n", "locales")
const PLURAL = /_(zero|one|two|few|many|other)$/
const CALL = /\bt\(\s*["'`]([^"'`$]+)["'`]/g
const NAMESPACE = /useTranslation\(\s*["']([a-z]+)["']\s*\)/

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
})
