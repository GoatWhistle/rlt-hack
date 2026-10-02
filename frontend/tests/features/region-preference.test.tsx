import { act, screen, waitFor, within } from "@testing-library/react"
import { en, text } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { useState } from "react"
import { describe, expect, it, vi } from "vitest"
import { RegionPreference } from "@/features/search-box/region-preference"
import type { Locale } from "@/shared/i18n/locale"
import { EXIT_FALLBACK_MS } from "@/shared/motion/use-presence"

function Harness(props: {
  readonly initial: string
  readonly disabled?: boolean
  readonly onChange: (value: string) => void
}) {
  const [value, setValue] = useState(props.initial)
  return (
    <>
      <RegionPreference
        value={value}
        disabled={props.disabled === true}
        onChange={(next) => {
          setValue(next)
          props.onChange(next)
        }}
      />
      <button type="button">outside</button>
    </>
  )
}

function renderPicker(initial = "78", locale: Locale = "en", disabled = false) {
  const onChange = vi.fn()
  const view = renderWithProviders(
    <Harness initial={initial} disabled={disabled} onChange={onChange} />,
    { locale },
  )
  const trigger = screen.getByRole("button", { name: /^(Delivery region|Регион поставки):/ })
  return { ...view, onChange, trigger }
}

function names() {
  return screen.getAllByRole("option").map((option) => option.textContent)
}

describe("the delivery region picker", () => {
  it("names the trigger after the region and lists cities before regions", async () => {
    const { user, trigger } = renderPicker()
    expect(trigger).toHaveAccessibleName("Delivery region: Saint Petersburg")
    expect(trigger).toHaveAttribute("aria-haspopup", "listbox")
    await user.click(trigger)
    expect(trigger).toHaveAttribute("aria-expanded", "true")
    const field = screen.getByRole("combobox", {
      name: en("box.regionPicker.search", "search"),
    })
    expect(field).toHaveFocus()
    const cities = screen.getByRole("group", { name: en("box.regionPicker.cities", "search") })
    const regions = screen.getByRole("group", {
      name: en("box.regionPicker.regions", "search"),
    })
    const cityNames = within(cities)
      .getAllByRole("option")
      .map((option) => option.textContent)
    expect(cityNames.slice(0, 3)).toEqual([
      "Saint Petersburg",
      "Moscow",
      "NovosibirskNovosibirsk Oblast",
    ])
    const regionNames = within(regions)
      .getAllByRole("option")
      .map((option) => option.textContent ?? "")
    expect(regionNames).toHaveLength(83)
    expect([...regionNames].sort((a, b) => a.localeCompare(b, "en"))).toEqual(regionNames)
    expect(names()[0]).toBe(en("box.anyRegion", "search"))
    const active = field.getAttribute("aria-activedescendant") ?? ""
    expect(document.getElementById(active)).toHaveAttribute("aria-selected", "true")
  })

  it("finds Saint Petersburg by its Russian nicknames, across languages and dashes", async () => {
    const { user, trigger } = renderPicker("", "ru")
    await user.click(trigger)
    const field = screen.getByRole("combobox")
    await user.type(field, "спб")
    expect(names()).toEqual([text("ru", "evidence", "cityName.78")])
    await user.clear(field)
    await user.type(field, "Питер")
    expect(names()[0]).toBe(text("ru", "evidence", "cityName.78"))
    await user.clear(field)
    await user.type(field, "Moscow")
    expect(names()[0]).toBe(text("ru", "evidence", "cityName.77"))
    await user.clear(field)
    await user.type(field, "санкт петербург")
    expect(names()).toEqual([text("ru", "evidence", "cityName.78")])
    expect(screen.queryAllByRole("group")).toHaveLength(0)
    await user.clear(field)
    expect(screen.getAllByRole("group")).toHaveLength(2)
  })

  it("highlights the matched part and shows a calm message when nothing matches", async () => {
    const { user, trigger } = renderPicker()
    await user.click(trigger)
    const field = screen.getByRole("combobox")
    await user.type(field, "kaz")
    const [first] = screen.getAllByRole("option")
    expect(first?.querySelector("mark")).toHaveTextContent("Kaz")
    await user.type(field, "qqq")
    expect(screen.queryAllByRole("option")).toHaveLength(0)
    expect(screen.getByRole("status")).toHaveTextContent(en("box.regionPicker.empty", "search"))
  })

  it("moves through the options from the keyboard and picks one with Enter", async () => {
    const { user, trigger, onChange } = renderPicker("")
    trigger.focus()
    await user.keyboard("{ArrowDown}")
    const field = screen.getByRole("combobox")
    const activeName = () =>
      document.getElementById(field.getAttribute("aria-activedescendant") ?? "")?.textContent
    expect(activeName()).toBe(en("box.anyRegion", "search"))
    await user.keyboard("{ArrowUp}")
    expect(activeName()).toBe(names().at(-1))
    await user.keyboard("{Home}{ArrowDown}{ArrowDown}")
    expect(activeName()).toBe("Moscow")
    await user.keyboard("{PageDown}")
    expect(activeName()).toBe(names()[10])
    await user.keyboard("{PageUp}{End}")
    expect(activeName()).toBe(names().at(-1))
    await user.keyboard("{Home}{ArrowDown}{ArrowDown}{Enter}")
    expect(onChange).toHaveBeenCalledWith("77")
    expect(trigger).toHaveFocus()
    expect(trigger).toHaveAccessibleName("Delivery region: Moscow")
  })

  it("opens by typing on the trigger and picks with the pointer", async () => {
    const { user, trigger, onChange } = renderPicker()
    trigger.focus()
    await user.keyboard("e")
    expect(screen.getByRole("combobox")).toHaveValue("e")
    await user.clear(screen.getByRole("combobox"))
    await user.type(screen.getByRole("combobox"), "ekb")
    const option = screen.getByRole("option", { name: /Yekaterinburg/ })
    await user.hover(option)
    await user.click(option)
    expect(onChange).toHaveBeenCalledWith("66")
  })

  it("closes on Escape with the focus back on the trigger", async () => {
    const { user, trigger } = renderPicker()
    await user.click(trigger)
    await user.keyboard("{Escape}")
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    expect(trigger).toHaveFocus()
    await act(() => new Promise((resolve) => setTimeout(resolve, EXIT_FALLBACK_MS + 50)))
    expect(screen.queryByRole("listbox")).toBeNull()
  })

  it("closes on Tab, on the close button and on a press outside", async () => {
    const { user, trigger, onChange } = renderPicker()
    await user.click(trigger)
    await user.keyboard("{Tab}")
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    await user.click(trigger)
    await user.click(
      screen.getByRole("button", { name: en("box.regionPicker.close", "search") }),
    )
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    expect(trigger).toHaveFocus()
    await user.click(trigger)
    await user.click(screen.getByRole("button", { name: "outside" }))
    await waitFor(() => expect(trigger).toHaveAttribute("aria-expanded", "false"))
    await user.click(trigger)
    await user.click(trigger)
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    expect(onChange).not.toHaveBeenCalled()
  })

  it("stays closed while disabled", async () => {
    const { user, trigger } = renderPicker("78", "en", true)
    expect(trigger).toBeDisabled()
    await user.click(trigger)
    expect(screen.queryByRole("listbox")).toBeNull()
  })

  it("shows no regional preference as an empty choice", () => {
    const { trigger } = renderPicker("")
    expect(trigger).toHaveAccessibleName(`Delivery region: ${en("box.anyRegion", "search")}`)
  })
})
