export async function decodeFile(file: Blob): Promise<string> {
  const bytes = await file.arrayBuffer()
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes)
  } catch {
    return new TextDecoder("windows-1251").decode(bytes)
  }
}
