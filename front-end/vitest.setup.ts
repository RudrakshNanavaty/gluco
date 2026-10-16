import "@testing-library/jest-dom/vitest"

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== "undefined") {
  window.ResizeObserver = ResizeObserverMock
  global.ResizeObserver = ResizeObserverMock

  window.matchMedia =
    window.matchMedia ||
    function (query: string) {
      return {
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }
    }
}

if (typeof Element !== "undefined") {
  Element.prototype.hasPointerCapture = Element.prototype.hasPointerCapture || (() => false)
  Element.prototype.setPointerCapture = Element.prototype.setPointerCapture || (() => {})
  Element.prototype.releasePointerCapture = Element.prototype.releasePointerCapture || (() => {})
  Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || (() => {})
}
