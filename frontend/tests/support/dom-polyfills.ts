class AnimationEventPolyfill extends Event {
  readonly animationName: string
  readonly elapsedTime: number
  readonly pseudoElement: string

  constructor(type: string, init: AnimationEventInit = {}) {
    super(type, init)
    this.animationName = init.animationName ?? ""
    this.elapsedTime = init.elapsedTime ?? 0
    this.pseudoElement = init.pseudoElement ?? ""
  }
}

if (!("AnimationEvent" in window)) {
  Object.assign(window, { AnimationEvent: AnimationEventPolyfill })
}

const dialog = HTMLDialogElement.prototype

if (typeof dialog.showModal !== "function") {
  dialog.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "")
  }
  dialog.close = function close(this: HTMLDialogElement) {
    this.removeAttribute("open")
  }
}
