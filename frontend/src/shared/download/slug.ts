const CYRILLIC_START = 0x430
const CYRILLIC_YO = 0x451
const LATIN = [
  "a",
  "b",
  "v",
  "g",
  "d",
  "e",
  "zh",
  "z",
  "i",
  "y",
  "k",
  "l",
  "m",
  "n",
  "o",
  "p",
  "r",
  "s",
  "t",
  "u",
  "f",
  "kh",
  "ts",
  "ch",
  "sh",
  "shch",
  "",
  "y",
  "",
  "e",
  "yu",
  "ya",
]

function latinOf(char: string): string {
  const code = char.codePointAt(0) ?? 0
  if (code === CYRILLIC_YO) return "e"
  const latin = LATIN[code - CYRILLIC_START]
  if (latin !== undefined) return latin
  return /[a-z0-9]/.test(char) ? char : ""
}

export function slugOf(text: string, words = 3): string {
  return text
    .toLowerCase()
    .split(/[^\p{L}\p{N}]+/u)
    .map((word) => [...word].map(latinOf).join(""))
    .filter(Boolean)
    .slice(0, words)
    .join("-")
}
