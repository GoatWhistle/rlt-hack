import { VisuallyHidden } from "@/shared/ui/visually-hidden"

export type LoadingStateProps = {
  readonly label: string
}

export function LoadingState({ label }: LoadingStateProps) {
  return (
    <div role="status" aria-busy="true">
      <VisuallyHidden>{label}</VisuallyHidden>
    </div>
  )
}
