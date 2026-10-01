import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useRef, useState } from "react"
import { describe, expect, it, vi } from "vitest"
import { Menu, MenuItemRadio, nextIndex } from "@/shared/ui/menu"
import { placeIndicator } from "@/shared/ui/menu/use-checked-indicator"

function Harness({ onSelect = vi.fn() }: { readonly onSelect?: (value: string) => void }) {
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState("b")
  const trigger = useRef<HTMLButtonElement>(null)
  const close = (restore: boolean) => {
    setOpen(false)
    if (restore) trigger.current?.focus()
  }
  return (
    <>
      <button ref={trigger} type="button" onClick={() => setOpen((current) => !current)}>
        toggle
      </button>
      <button type="button">outside</button>
      <Menu id="menu" open={open} label="Options" triggerRef={trigger} onClose={close}>
        {["a", "b", "c"].map((item) => (
          <MenuItemRadio
            key={item}
            checked={item === value}
            onSelect={() => {
              setValue(item)
              onSelect(item)
              close(true)
            }}
          >
            {item}
          </MenuItemRadio>
        ))}
      </Menu>
    </>
  )
}

function finishExit() {
  const menu = screen.queryByRole("menu")
  if (menu) fireEvent.animationEnd(menu)
}

describe("Menu", () => {
  it("focuses the checked item on open and moves with the arrow keys", async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.click(screen.getByRole("button", { name: "toggle" }))
    expect(screen.getByRole("menuitemradio", { name: "b" })).toHaveFocus()
    await user.keyboard("{ArrowDown}")
    expect(screen.getByRole("menuitemradio", { name: "c" })).toHaveFocus()
    await user.keyboard("{ArrowDown}")
    expect(screen.getByRole("menuitemradio", { name: "a" })).toHaveFocus()
    await user.keyboard("{ArrowUp}")
    expect(screen.getByRole("menuitemradio", { name: "c" })).toHaveFocus()
    await user.keyboard("{Home}")
    expect(screen.getByRole("menuitemradio", { name: "a" })).toHaveFocus()
    await user.keyboard("{End}")
    expect(screen.getByRole("menuitemradio", { name: "c" })).toHaveFocus()
  })

  it("closes on escape and gives focus back to the trigger", async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.click(screen.getByRole("button", { name: "toggle" }))
    await user.keyboard("{Escape}")
    finishExit()
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "toggle" })).toHaveFocus()
  })

  it("closes on tab and on a click outside, but not on a click inside", async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.click(screen.getByRole("button", { name: "toggle" }))
    fireEvent.pointerDown(screen.getByRole("menu"))
    expect(screen.getByRole("menu")).toHaveAttribute("data-state", "open")
    fireEvent.pointerDown(screen.getByRole("button", { name: "outside" }))
    expect(screen.getByRole("menu")).toHaveAttribute("data-state", "closed")
    finishExit()
    await user.click(screen.getByRole("button", { name: "toggle" }))
    await user.keyboard("{Tab}")
    expect(screen.getByRole("menu")).toHaveAttribute("data-state", "closed")
  })

  it("reports the chosen item and marks it checked", async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(<Harness onSelect={onSelect} />)
    await user.click(screen.getByRole("button", { name: "toggle" }))
    await user.click(screen.getByRole("menuitemradio", { name: "c" }))
    expect(onSelect).toHaveBeenCalledWith("c")
    finishExit()
    await user.click(screen.getByRole("button", { name: "toggle" }))
    expect(screen.getByRole("menuitemradio", { name: "c" })).toHaveAttribute(
      "aria-checked",
      "true",
    )
    await user.keyboard("x")
    expect(screen.getByRole("menuitemradio", { name: "c" })).toHaveFocus()
  })

  it("ignores keys that do not move focus", () => {
    expect(nextIndex("x", 0, 3)).toBeNull()
  })
})

describe("checked indicator", () => {
  function menuWith(checkedTop: number | null) {
    const menu = document.createElement("div")
    for (const top of [4, 44]) {
      const item = document.createElement("button")
      item.setAttribute("aria-checked", String(top === checkedTop))
      Object.defineProperty(item, "offsetTop", { value: top })
      Object.defineProperty(item, "offsetHeight", { value: 40 })
      menu.append(item)
    }
    return menu
  }

  it("sits under the checked item and keeps its animation once ready", () => {
    const menu = menuWith(44)
    expect(placeIndicator(menu)).toBe(true)
    expect(menu.dataset.indicator).toBe("placed")
    expect(menu.style.getPropertyValue("--indicator-y")).toBe("44px")
    expect(menu.style.getPropertyValue("--indicator-height")).toBe("40px")
    menu.dataset.indicator = "ready"
    placeIndicator(menu)
    expect(menu.dataset.indicator).toBe("ready")
  })

  it("hides when nothing is checked", () => {
    const menu = menuWith(null)
    expect(placeIndicator(menu)).toBe(false)
    expect(menu.dataset.indicator).toBe("hidden")
  })

  it("turns on its transition after the first frame", async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.click(screen.getByRole("button", { name: "toggle" }))
    await waitFor(() =>
      expect(screen.getByRole("menu")).toHaveAttribute("data-indicator", "ready"),
    )
  })
})
