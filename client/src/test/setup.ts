import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
import { afterEach, vi } from "vitest"

// jsdom implements the DOM, not a browser. These three gaps are all things
// the app genuinely calls, so without them the failure looks like a bug in
// the component rather than a missing browser API.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn()
}

if (!globalThis.crypto?.randomUUID) {
  Object.defineProperty(globalThis.crypto, "randomUUID", {
    configurable: true,
    value: () => "00000000-0000-4000-8000-000000000000",
  })
}

if (!URL.createObjectURL) {
  URL.createObjectURL = vi.fn(() => "blob:test")
  URL.revokeObjectURL = vi.fn()
}

afterEach(() => {
  cleanup()
})
