export type CsvRecord = {
  readonly line: number
  readonly cells: readonly string[]
}

const DELIMITERS = [";", ",", "\t"] as const

export function detectDelimiter(text: string): string {
  const firstLine = text.slice(0, text.search(/\r?\n|$/))
  const scores = DELIMITERS.map((delimiter) => firstLine.split(delimiter).length)
  const best = Math.max(...scores)
  return DELIMITERS[scores.indexOf(best)] ?? ";"
}

class CsvTokenizer {
  readonly records: CsvRecord[] = []
  private cells: string[] = []
  private cell = ""
  private quoted = false
  private line = 1
  private start = 1
  private readonly delimiter: string

  constructor(delimiter: string) {
    this.delimiter = delimiter
  }

  quotedChar(char: string, next: string | undefined): number {
    if (char === '"' && next === '"') {
      this.cell += '"'
      return 2
    }
    if (char === '"') this.quoted = false
    else {
      if (char === "\n") this.line += 1
      this.cell += char
    }
    return 1
  }

  plainChar(char: string): void {
    if (char === '"') this.quoted = true
    else if (char === this.delimiter) this.endCell()
    else if (char === "\n") this.endRecord()
    else if (char !== "\r") this.cell += char
  }

  read(text: string): CsvRecord[] {
    let index = 0
    while (index < text.length) {
      const char = text[index] ?? ""
      if (this.quoted) index += this.quotedChar(char, text[index + 1])
      else {
        this.plainChar(char)
        index += 1
      }
    }
    if (this.cell.length > 0 || this.cells.length > 0) this.finish()
    return this.records
  }

  private endCell(): void {
    this.cells.push(this.cell)
    this.cell = ""
  }

  private finish(): void {
    this.endCell()
    if (this.cells.some((cell) => cell.trim().length > 0)) {
      this.records.push({ line: this.start, cells: this.cells })
    }
    this.cells = []
  }

  private endRecord(): void {
    this.finish()
    this.line += 1
    this.start = this.line
  }
}

export function readCsv(text: string, delimiter = detectDelimiter(text)): CsvRecord[] {
  return new CsvTokenizer(delimiter).read(text)
}
