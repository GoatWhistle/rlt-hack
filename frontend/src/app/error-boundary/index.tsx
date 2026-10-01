import { Component, type ErrorInfo, type ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { reloadPage } from "@/shared/errors/reload-page"
import { Button } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"

export type CrashScreenProps = {
  readonly onReload: () => void
}

export function CrashScreen({ onReload }: CrashScreenProps) {
  const { t } = useTranslation()
  return (
    <EmptyState
      tone="error"
      title={t("crash.title")}
      description={t("crash.description")}
      actions={<Button onClick={onReload}>{t("action.reload")}</Button>}
    />
  )
}

export type AppErrorBoundaryProps = {
  readonly children: ReactNode
  readonly onReload?: () => void
}

type AppErrorBoundaryState = {
  readonly failed: boolean
}

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  override state: AppErrorBoundaryState = { failed: false }

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { failed: true }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(error, info.componentStack)
  }

  override render(): ReactNode {
    if (!this.state.failed) return this.props.children
    return <CrashScreen onReload={this.props.onReload ?? reloadPage} />
  }
}
