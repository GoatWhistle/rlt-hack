import { describe, expect, it } from "vitest"
import { packageSize, SOURCE_LIMIT, TEST_LIMIT } from "../../scripts/checks/package-size.ts"
import { packageSubject } from "../../scripts/checks/package-subject.ts"
import { file } from "./fixtures.ts"

function many(directory: string, count: number, extension = "ts") {
  return Array.from({ length: count }, (_, index) =>
    file(`${directory}/f${index}.${extension}`, ""),
  )
}

describe("package size", () => {
  it("rejects a source package over the limit", () => {
    const found = packageSize.check(many("src/features/big", SOURCE_LIMIT + 1))
    expect(found.map((violation) => violation.path)).toEqual(["src/features/big"])
  })

  it("gives tests a larger limit", () => {
    expect(packageSize.check(many("tests/features", SOURCE_LIMIT + 1))).toEqual([])
    expect(packageSize.check(many("tests/features", TEST_LIMIT + 1))).toHaveLength(1)
  })

  it("does not count declarations, styles or root files", () => {
    expect(
      packageSize.check([
        ...many("src/types", SOURCE_LIMIT + 1, "d.ts"),
        ...many("src/styles", SOURCE_LIMIT + 1, "css"),
        ...many(".", SOURCE_LIMIT + 1).map((entry) => file(entry.path.slice(2), "")),
      ]),
    ).toEqual([])
  })
})

describe("package subject", () => {
  it("rejects packages named by reuse", () => {
    const found = packageSubject.check([
      file("src/features/utils/a.ts", ""),
      file("src/shared/lib/b.ts", ""),
      file("tests/helpers/c.ts", ""),
    ])
    expect(found.map((violation) => violation.path)).toEqual([
      "src/features/utils",
      "src/shared/lib",
      "tests/helpers",
    ])
  })

  it("accepts the shared layer and subject names", () => {
    expect(
      packageSubject.check([
        file("src/shared/ui/button/index.tsx", ""),
        file("tests/shared/ui/button.test.tsx", ""),
        file("scripts/utils/x.ts", ""),
      ]),
    ).toEqual([])
  })
})
