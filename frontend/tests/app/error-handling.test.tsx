import { QueryClientProvider, useMutation } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { createMemoryRouter, RouterProvider } from "react-router"
import { describe, expect, it, vi } from "vitest"
import { AppErrorBoundary } from "@/app/error-boundary"
import { useMutationErrorToasts } from "@/app/mutation-error-toasts"
import { RouteErrorPage } from "@/pages/route-error"
import { ApiError } from "@/shared/api/api-error"
import { createQueryClient } from "@/shared/api/query-client"
import { LocaleProvider } from "@/shared/i18n/locale-provider"
import { Button } from "@/shared/ui/button"
import { ToastProvider } from "@/shared/ui/toast"

function renderFailingRoute(failure: unknown, onReload = vi.fn()) {
  const loader = vi.fn(() => {
    throw failure
  })
  const router = createMemoryRouter([
    {
      path: "/",
      loader,
      Component: () => null,
      ErrorBoundary: () => <RouteErrorPage onReload={onReload} />,
    },
  ])
  render(
    <LocaleProvider initialLocale="en">
      <QueryClientProvider client={createQueryClient()}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </LocaleProvider>,
  )
  return { loader, onReload, user: userEvent.setup() }
}

function Explode(): never {
  throw new Error("render failed")
}

function MutationProbe({ silent = false }: { readonly silent?: boolean }) {
  const mutation = useMutation({
    mutationFn: () => Promise.reject(new ApiError({ status: 403, code: "http_403" })),
    meta: { silent },
  })
  return <Button onClick={() => mutation.mutate()}>save</Button>
}

describe("route errors", () => {
  it("explain an api failure, show its code and retry the loader", async () => {
    const { loader, user } = renderFailingRoute(new ApiError({ status: 503, code: "http_503" }))
    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent(en("server", "errors"))
    expect(alert).toHaveTextContent("http_503")
    expect(screen.getByRole("link", { name: en("action.home") })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: en("action.retry") }))
    await vi.waitFor(() => expect(loader).toHaveBeenCalledTimes(2))
  })

  it("show the not found page for a missing resource", async () => {
    renderFailingRoute(new Response(null, { status: 404 }))
    expect(
      await screen.findByRole("heading", { name: en("notFound.title") }),
    ).toBeInTheDocument()
  })

  it("ask for a reload when a new version replaced the code", async () => {
    const chunk = new TypeError("Failed to fetch dynamically imported module")
    const { onReload, user } = renderFailingRoute(chunk)
    await user.click(await screen.findByRole("button", { name: en("action.reload") }))
    expect(
      screen.getByRole("heading", { name: en("updateRequired.title") }),
    ).toBeInTheDocument()
    expect(onReload).toHaveBeenCalledOnce()
  })
})

describe("the root error boundary", () => {
  it("replaces a crashed tree with a reload screen", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined)
    const onReload = vi.fn()
    render(
      <LocaleProvider initialLocale="en">
        <AppErrorBoundary onReload={onReload}>
          <Explode />
        </AppErrorBoundary>
      </LocaleProvider>,
    )
    expect(screen.getByRole("heading", { name: en("crash.title") })).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole("button", { name: en("action.reload") }))
    expect(onReload).toHaveBeenCalledOnce()
    expect(consoleError).toHaveBeenCalled()
    consoleError.mockRestore()
  })

  it("renders children while nothing fails", () => {
    render(
      <LocaleProvider initialLocale="en">
        <AppErrorBoundary>
          <p>fine</p>
        </AppErrorBoundary>
      </LocaleProvider>,
    )
    expect(screen.getByText("fine")).toBeInTheDocument()
  })
})

describe("mutation errors", () => {
  function Bridge({ silent }: { readonly silent?: boolean }) {
    return <MutationProbe silent={silent} />
  }

  function renderWithBridge(silent: boolean) {
    const queryClient = createQueryClient()
    function Toasts() {
      useMutationErrorToasts(queryClient)
      return null
    }
    render(
      <LocaleProvider initialLocale="en">
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <Toasts />
            <Bridge silent={silent} />
          </ToastProvider>
        </QueryClientProvider>
      </LocaleProvider>,
    )
    return userEvent.setup()
  }

  it("surface as an error toast in the current language", async () => {
    const user = renderWithBridge(false)
    await user.click(screen.getByRole("button", { name: "save" }))
    expect(await screen.findByRole("alert")).toHaveTextContent(en("forbidden", "errors"))
  })

  it("stay quiet when the mutation asks for silence", async () => {
    const user = renderWithBridge(true)
    await user.click(screen.getByRole("button", { name: "save" }))
    await new Promise((resolve) => setTimeout(resolve, 20))
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("render inside the shared test providers", () => {
    renderWithProviders(<MutationProbe />)
    expect(screen.getByRole("button", { name: "save" })).toBeInTheDocument()
  })
})
