export type JsonStorage = {
  readonly read: (key: string) => unknown
  readonly write: (key: string, value: unknown) => boolean
}

export function createJsonStorage(storage: () => Storage = () => window.localStorage) {
  return {
    read: (key: string): unknown => {
      try {
        const raw = storage().getItem(key)
        return raw === null ? undefined : JSON.parse(raw)
      } catch {
        return undefined
      }
    },
    write: (key: string, value: unknown): boolean => {
      try {
        storage().setItem(key, JSON.stringify(value))
        return true
      } catch {
        return false
      }
    },
  } satisfies JsonStorage
}

export const localJson: JsonStorage = createJsonStorage()
