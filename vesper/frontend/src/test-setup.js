import '@testing-library/jest-dom'

// Node 25 injects a broken localStorage global (SQLite-backed, no .clear())
// that overrides jsdom's. Replace it with a simple Map-backed implementation.
const store = new Map()
const localStorageMock = {
  getItem: (k) => store.get(k) ?? null,
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
  clear: () => store.clear(),
  get length() { return store.size },
  key: (i) => [...store.keys()][i] ?? null,
}
Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
  writable: true,
  configurable: true,
})

// Mock HTMLCanvasElement.getContext for ParticleOrb component tests
HTMLCanvasElement.prototype.getContext = () => ({
  fillStyle: '',
  fillRect: () => {},
  strokeStyle: '',
  lineWidth: 0,
  beginPath: () => {},
  moveTo: () => {},
  lineTo: () => {},
  stroke: () => {},
  arc: () => {},
  fill: () => {},
  shadowColor: '',
  shadowBlur: 0,
})

// Mock requestAnimationFrame for ParticleOrb animation loop
globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 16)
