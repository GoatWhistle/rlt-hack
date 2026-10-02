import { useEffect, useRef, useState } from "react"

function carriesFiles(event: DragEvent): boolean {
  return Array.from(event.dataTransfer?.types ?? []).includes("Files")
}

export function useWindowDrop(onFile: (file: File) => void, enabled = true): boolean {
  const [dragging, setDragging] = useState(false)
  const handler = useRef(onFile)
  useEffect(() => {
    handler.current = onFile
  }, [onFile])

  useEffect(() => {
    if (!enabled) return
    let depth = 0
    const enter = (event: DragEvent) => {
      if (!carriesFiles(event)) return
      event.preventDefault()
      depth += 1
      setDragging(true)
    }
    const over = (event: DragEvent) => {
      if (!carriesFiles(event)) return
      event.preventDefault()
      if (event.dataTransfer) event.dataTransfer.dropEffect = "copy"
    }
    const leave = (event: DragEvent) => {
      if (!carriesFiles(event)) return
      depth = Math.max(0, depth - 1)
      if (depth === 0) setDragging(false)
    }
    const drop = (event: DragEvent) => {
      if (!carriesFiles(event)) return
      event.preventDefault()
      depth = 0
      setDragging(false)
      const file = event.dataTransfer?.files[0]
      if (file) handler.current(file)
    }
    const listeners: readonly (readonly [string, (event: DragEvent) => void])[] = [
      ["dragenter", enter],
      ["dragover", over],
      ["dragleave", leave],
      ["drop", drop],
    ]
    for (const [name, listener] of listeners)
      window.addEventListener(name, listener as EventListener)
    return () => {
      for (const [name, listener] of listeners) {
        window.removeEventListener(name, listener as EventListener)
      }
      setDragging(false)
    }
  }, [enabled])

  return dragging
}
