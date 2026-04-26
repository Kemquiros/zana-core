import '@testing-library/jest-dom'

// Mock matchMedia for testing
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock window.scrollTo
window.scrollTo = jest.fn()

// Mock EventSource
class MockEventSource {
  onmessage: any;
  onerror: any;
  close = jest.fn();
  constructor(url: string) {}
}
Object.defineProperty(window, 'EventSource', {
  writable: true,
  value: MockEventSource
});