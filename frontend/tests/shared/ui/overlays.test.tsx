import { act, fireEvent, renderHook, screen } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { useState } from "react"
import { describe, expect, it, vi } from "vitest"
import { EXIT_FALLBACK_MS } from "@/shared/motion/use-presence"
import { Button } from "@/shared/ui/button"
import { Dialog } from "@/shared/ui/dialog"
import { DEFAULT_TOAST_MS, ERROR_TOAST_MS, MAX_TOASTS } from "@/shared/ui/toast"
import { useToast } from "@/shared/ui/toast/toast-context"

function DialogHarness({ onClose }: { readonly onClose?: () => void }) {
  const [open, setOpen] = useState(false)
  const close = () => {
    onClose?.()
    setOpen(false)
  }
  return (
    <>
      <Button onClick={() => setOpen(true)}>open</Button>
      <Dialog open={open} title="Details" onClose={close} footer={<span>footer</span>}>
        <p>body</p>
      </Dialog>
    </>
  )
}

function ToastHarness({ tone }: { readonly tone?: "info" | "success" | "error" }) {
  const { show } = useToast()
  return <Button onClick={() => show({ message: `saved ${Date.now()}`, tone })}>notify</Button>
}

describe("Dialog", () => {
  it("opens as a modal and closes with an exit animation", async () => {
    const { user } = renderWithProviders(<DialogHarness />)
    await user.click(screen.getByRole("button", { name: "open" }))
    const dialog = screen.getByRole("dialog", { name: "Details" })
    expect(dialog).toHaveAttribute("open")
    expect(screen.getByRole("heading", { name: "Details" })).toHaveFocus()
    expect(
      Array.from(dialog.querySelectorAll("button, span")).map((node) => node.textContent),
    ).toEqual([en("action.close"), "footer"])
    expect(dialog).toHaveAttribute("data-state", "open")
    await user.click(screen.getByRole("button", { name: en("action.close") }))
    expect(dialog).toHaveAttribute("data-state", "closed")
    fireEvent.animationEnd(dialog)
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("closes on escape and on a backdrop click, not on a content click", async () => {
    const onClose = vi.fn()
    const { user } = renderWithProviders(<DialogHarness onClose={onClose} />)
    await user.click(screen.getByRole("button", { name: "open" }))
    fireEvent.click(screen.getByText("body"))
    expect(onClose).not.toHaveBeenCalled()
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }))
    expect(onClose).toHaveBeenCalledTimes(1)
    await user.click(screen.getByRole("button", { name: "open" }))
    fireEvent.click(screen.getByRole("dialog"))
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})

function toasts() {
  return screen.getByRole("region", { name: en("notifications.label") })
}

describe("Toasts", () => {
  it("announces a status politely and dismisses it after its duration", () => {
    vi.useFakeTimers()
    renderWithProviders(<ToastHarness tone="success" />)
    fireEvent.click(screen.getByRole("button", { name: "notify" }))
    const toast = toasts().querySelector("li")
    expect(toast).toHaveAttribute("data-state", "open")
    expect(toasts().querySelector("[aria-live='polite']")).toHaveTextContent(/saved/)
    act(() => vi.advanceTimersByTime(DEFAULT_TOAST_MS))
    expect(toast).toHaveAttribute("data-state", "closed")
    act(() => vi.advanceTimersByTime(EXIT_FALLBACK_MS))
    expect(toasts().querySelector("li")).toBeNull()
  })

  it("keeps a toast while it is hovered or focused", () => {
    vi.useFakeTimers()
    renderWithProviders(<ToastHarness />)
    fireEvent.click(screen.getByRole("button", { name: "notify" }))
    const toast = toasts().querySelector("li") as HTMLElement
    act(() => vi.advanceTimersByTime(DEFAULT_TOAST_MS - 1000))
    fireEvent.pointerEnter(toast)
    act(() => vi.advanceTimersByTime(DEFAULT_TOAST_MS * 2))
    expect(toast).toHaveAttribute("data-state", "open")
    fireEvent.pointerLeave(toast)
    fireEvent.focus(screen.getByRole("button", { name: en("action.dismiss") }))
    act(() => vi.advanceTimersByTime(DEFAULT_TOAST_MS * 2))
    expect(toast).toHaveAttribute("data-state", "open")
    fireEvent.blur(screen.getByRole("button", { name: en("action.dismiss") }))
    act(() => vi.advanceTimersByTime(999))
    expect(toast).toHaveAttribute("data-state", "open")
    act(() => vi.advanceTimersByTime(1))
    expect(toast).toHaveAttribute("data-state", "closed")
  })

  it("announces errors assertively, keeps them longer and closes them by hand", () => {
    vi.useFakeTimers()
    renderWithProviders(<ToastHarness tone="error" />)
    fireEvent.click(screen.getByRole("button", { name: "notify" }))
    const toast = toasts().querySelector("li") as HTMLElement
    expect(toasts().querySelector("[aria-live='assertive']")).toHaveTextContent(/saved/)
    act(() => vi.advanceTimersByTime(ERROR_TOAST_MS - 1))
    expect(toast).toHaveAttribute("data-state", "open")
    fireEvent.click(screen.getByRole("button", { name: en("action.dismiss") }))
    fireEvent.animationEnd(toast)
    expect(toasts().querySelector("li")).toBeNull()
  })

  it("keeps only the latest toasts in a labelled region", () => {
    renderWithProviders(<ToastHarness />)
    for (let index = 0; index <= MAX_TOASTS; index++) {
      fireEvent.click(screen.getByRole("button", { name: "notify" }))
    }
    const region = screen.getByRole("region", { name: en("notifications.label") })
    expect(region.querySelectorAll("li")).toHaveLength(MAX_TOASTS)
  })

  it("refuses to be used without a provider", () => {
    expect(() => renderHook(() => useToast())).toThrow(
      "useToast must be used within ToastProvider",
    )
  })
})
