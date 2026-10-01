import { act, fireEvent, render, renderHook, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { EXIT_FALLBACK_MS, usePresence } from "@/shared/motion/use-presence"
import { Transition } from "@/shared/ui/transition"

afterEach(() => {
  vi.useRealTimers()
})

describe("usePresence", () => {
  it("mounts on open and stays mounted while closing", () => {
    const { result, rerender } = renderHook(({ open }) => usePresence(open), {
      initialProps: { open: false },
    })
    expect(result.current.isMounted).toBe(false)
    rerender({ open: true })
    expect(result.current).toMatchObject({ isMounted: true, state: "open" })
    rerender({ open: false })
    expect(result.current).toMatchObject({ isMounted: true, state: "closed" })
  })

  it("unmounts by the fallback timer when no animation ends", () => {
    vi.useFakeTimers()
    const { result, rerender } = renderHook(({ open }) => usePresence(open), {
      initialProps: { open: true },
    })
    rerender({ open: false })
    act(() => vi.advanceTimersByTime(EXIT_FALLBACK_MS))
    expect(result.current.isMounted).toBe(false)
  })
})

describe("Transition", () => {
  it("animates in, out and unmounts when its own exit animation ends", () => {
    const { rerender } = render(
      <Transition show preset="scale" data-testid="panel">
        <span data-testid="child" />
      </Transition>,
    )
    const panel = screen.getByTestId("panel")
    expect(panel).toHaveAttribute("data-state", "open")
    rerender(
      <Transition show={false} preset="scale" data-testid="panel">
        <span data-testid="child" />
      </Transition>,
    )
    expect(panel).toHaveAttribute("data-state", "closed")
    fireEvent.animationEnd(screen.getByTestId("child"))
    expect(screen.getByTestId("panel")).toBeInTheDocument()
    fireEvent.animationEnd(panel)
    expect(screen.queryByTestId("panel")).not.toBeInTheDocument()
  })

  it("ignores an animation end while open and renders nothing when hidden", () => {
    const { rerender } = render(<Transition show data-testid="panel" />)
    fireEvent.animationEnd(screen.getByTestId("panel"))
    expect(screen.getByTestId("panel")).toBeInTheDocument()
    rerender(<Transition show={false} preset="slide" data-testid="panel" />)
    fireEvent.animationEnd(screen.getByTestId("panel"))
    rerender(<Transition show={false} data-testid="panel" />)
    expect(screen.queryByTestId("panel")).not.toBeInTheDocument()
  })
})
