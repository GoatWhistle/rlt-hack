import { useCallback, useRef, useState } from "react"
import { intakeFile } from "./inspect"
import type { Intake } from "./model"

export type FileIntake = {
  readonly intake: Intake | null
  readonly attach: (file: File) => void
  readonly clear: () => void
}

export function useFileIntake(): FileIntake {
  const [intake, setIntake] = useState<Intake | null>(null)
  const latest = useRef(0)
  const attach = useCallback((file: File) => {
    latest.current += 1
    const ticket = latest.current
    setIntake({ status: "reading", file })
    void intakeFile(file).then((next) => {
      if (latest.current === ticket) setIntake(next)
    })
  }, [])
  const clear = useCallback(() => {
    latest.current += 1
    setIntake(null)
  }, [])
  return { intake, attach, clear }
}
