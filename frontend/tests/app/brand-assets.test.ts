import { readFileSync } from "node:fs"
import { join, resolve } from "node:path"
import { describe, expect, it } from "vitest"
import { BRAND_MARK_PATHS } from "@/shared/ui/brand-mark"

const ROOT = resolve(process.cwd())
const PUBLIC = join(ROOT, "public")

type ManifestIcon = { readonly src: string; readonly sizes: string; readonly purpose: string }

function publicFile(href: string): Buffer {
  return readFileSync(join(PUBLIC, href.replace(/^\//, "")))
}

function pngSize(data: Buffer): string {
  expect(data.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a")
  return `${data.readUInt32BE(16)}x${data.readUInt32BE(20)}`
}

function iconLinks(): { readonly href: string; readonly sizes: string | null }[] {
  const html = readFileSync(join(ROOT, "index.html"), "utf8")
  return [...html.matchAll(/<link\s+([^>]*rel="(?:icon|apple-touch-icon)"[^>]*)\/>/g)].map(
    ([, attributes = ""]) => ({
      href: /href="([^"]+)"/.exec(attributes)?.[1] ?? "",
      sizes: /sizes="([^"]+)"/.exec(attributes)?.[1] ?? null,
    }),
  )
}

describe("favicons", () => {
  it("link only files that exist and match their declared size", () => {
    const links = iconLinks()
    expect(links.length).toBeGreaterThanOrEqual(5)
    for (const { href, sizes } of links) {
      const data = publicFile(href)
      if (href.endsWith(".png") && sizes) expect(pngSize(data), href).toBe(sizes)
    }
  })

  it("pack 16, 32 and 48 px images into the ico", () => {
    const ico = publicFile("favicon.ico")
    const count = ico.readUInt16LE(4)
    const sizes = Array.from({ length: count }, (_, index) => ico.readUInt8(6 + index * 16))
    expect(sizes.sort((left, right) => left - right)).toEqual([16, 32, 48])
  })

  it("draw the same mark in the svg favicon as in the header", () => {
    const svg = publicFile("favicon.svg").toString("utf8")
    expect(svg).toContain(BRAND_MARK_PATHS.letter)
    expect(svg).toContain(BRAND_MARK_PATHS.facet)
  })
})

describe("platform icons", () => {
  const html = readFileSync(join(ROOT, "index.html"), "utf8")

  it("give Safari a single-colour pinned tab mask", () => {
    expect(html).toContain('<link rel="mask-icon" href="/safari-pinned-tab.svg"')
    const mask = publicFile("safari-pinned-tab.svg").toString("utf8")
    expect(mask).toContain(BRAND_MARK_PATHS.letter)
    expect(mask).not.toMatch(/fill=/)
  })

  it("give Windows a tile through browserconfig", () => {
    expect(html).toContain('<meta name="msapplication-config" content="/browserconfig.xml" />')
    const config = publicFile("browserconfig.xml").toString("utf8")
    const tile = /square150x150logo src="([^"]+)"/.exec(config)?.[1] ?? ""
    expect(pngSize(publicFile(tile))).toBe("150x150")
  })

  it("offer apple touch icons for every current iOS size", () => {
    const sizes = iconLinks()
      .filter(({ href }) => href.includes("apple-touch-icon"))
      .map(({ sizes }) => sizes)
    expect(sizes).toEqual(["180x180", "167x167", "152x152", "120x120", "76x76"])
  })
})

describe("web manifest", () => {
  const manifest = JSON.parse(publicFile("site.webmanifest").toString("utf8")) as {
    readonly name: string
    readonly theme_color: string
    readonly icons: readonly ManifestIcon[]
  }

  it("names the product and matches the header colour", () => {
    expect(manifest.name).toBe("Lotive")
    const html = readFileSync(join(ROOT, "index.html"), "utf8")
    expect(html).toContain(`<meta name="theme-color" content="${manifest.theme_color}" />`)
  })

  it("lists icons that exist with the declared sizes", () => {
    for (const icon of manifest.icons) {
      const data = publicFile(icon.src)
      if (icon.src.endsWith(".svg")) expect(data.toString("utf8")).toContain("<svg")
      else expect(pngSize(data), icon.src).toBe(icon.sizes)
    }
  })

  it("covers regular, maskable and monochrome purposes for Android", () => {
    const purposes = new Set(manifest.icons.map((icon) => icon.purpose))
    expect([...purposes].sort()).toEqual(["any", "maskable", "monochrome"])
    const maskable = manifest.icons.filter((icon) => icon.purpose === "maskable")
    expect(maskable.map((icon) => icon.sizes).sort()).toEqual(["192x192", "512x512"])
  })

  it("keeps a separate maskable icon and a transparent-cornered regular one", () => {
    const regular = manifest.icons.find(
      (icon) => icon.purpose === "any" && icon.sizes === "512x512",
    )
    const maskable = manifest.icons.find((icon) => icon.purpose === "maskable")
    expect(regular && maskable).toBeTruthy()
    expect(publicFile(regular?.src ?? "").equals(publicFile(maskable?.src ?? ""))).toBe(false)
  })
})
