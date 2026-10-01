import type { Locale } from "@/shared/i18n/locale"
import { type Namespace, resources } from "@/shared/i18n/resources"

export type Tree = { readonly [key: string]: string | Tree }

export function leaves(tree: Tree, prefix = ""): [string, string][] {
  return Object.entries(tree).flatMap(([key, value]): [string, string][] => {
    const path = prefix ? `${prefix}.${key}` : key
    return typeof value === "string" ? [[path, value]] : leaves(value, path)
  })
}

export function dictionary(locale: Locale, namespace: Namespace): Tree {
  return resources[locale][namespace] as Tree
}

export function text(locale: Locale, namespace: Namespace, path: string): string {
  const node = path
    .split(".")
    .reduce<string | Tree | undefined>(
      (current, part) => (current && typeof current === "object" ? current[part] : undefined),
      dictionary(locale, namespace),
    )
  if (typeof node !== "string") throw new Error(`missing ${locale}/${namespace}:${path}`)
  return node
}

export function en(path: string, namespace: Namespace = "common"): string {
  return text("en", namespace, path)
}
