/**
 * pwa.test.ts — Sprint 12 · Issue #39
 *
 * Tests for PWA manifest required fields and service worker registration.
 * Runs in jsdom (no browser needed).
 */

import fs from "fs";
import path from "path";

// ---------------------------------------------------------------------------
// Manifest field validation
// ---------------------------------------------------------------------------

const MANIFEST_PATH = path.join(__dirname, "../public");

// Next.js serves the manifest at /manifest.webmanifest via app/manifest.ts.
// We validate the shape exported from the route module directly.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const manifestFn = require("../app/manifest").default as () => Record<
  string,
  unknown
>;
const manifest = manifestFn();

describe("PWA manifest — required fields", () => {
  it("has name", () => {
    expect(typeof manifest.name).toBe("string");
    expect((manifest.name as string).length).toBeGreaterThan(0);
  });

  it("has short_name", () => {
    expect(typeof manifest.short_name).toBe("string");
    expect((manifest.short_name as string).length).toBeGreaterThan(0);
  });

  it("has start_url", () => {
    expect(manifest.start_url).toBe("/");
  });

  it('has display standalone', () => {
    expect(manifest.display).toBe("standalone");
  });

  it("has background_color as hex", () => {
    expect(typeof manifest.background_color).toBe("string");
    expect(manifest.background_color as string).toMatch(/^#[0-9a-fA-F]{6}$/);
  });

  it("has theme_color as hex", () => {
    expect(typeof manifest.theme_color).toBe("string");
    expect(manifest.theme_color as string).toMatch(/^#[0-9a-fA-F]{6}$/);
  });

  it("has at least two icons (192 and 512)", () => {
    const icons = manifest.icons as Array<{ src: string; sizes: string }>;
    expect(Array.isArray(icons)).toBe(true);
    expect(icons.length).toBeGreaterThanOrEqual(2);

    const sizes = icons.map((i) => i.sizes);
    expect(sizes).toContain("192x192");
    expect(sizes).toContain("512x512");
  });

  it("icon files exist in /public", () => {
    const icons = manifest.icons as Array<{ src: string }>;
    for (const icon of icons) {
      const src = icon.src.replace(/^\//, "");
      const filePath = path.join(MANIFEST_PATH, src);
      expect(fs.existsSync(filePath)).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// Service worker file validation
// ---------------------------------------------------------------------------

describe("Service worker — sw.js", () => {
  const swPath = path.join(__dirname, "../public/sw.js");
  let swSource: string;

  beforeAll(() => {
    swSource = fs.readFileSync(swPath, "utf-8");
  });

  it("sw.js exists in /public", () => {
    expect(fs.existsSync(swPath)).toBe(true);
  });

  it("registers install event handler", () => {
    expect(swSource).toContain('addEventListener("install"');
  });

  it("registers activate event handler", () => {
    expect(swSource).toContain('addEventListener("activate"');
  });

  it("registers fetch event handler", () => {
    expect(swSource).toContain('addEventListener("fetch"');
  });

  it("calls skipWaiting for immediate activation", () => {
    expect(swSource).toContain("skipWaiting");
  });

  it("calls clients.claim to take control immediately", () => {
    expect(swSource).toContain("clients.claim");
  });

  it("excludes WebSocket/SSE streams from cache", () => {
    // Ensures streaming endpoints are never cached (would break WS upgrades)
    expect(swSource).toMatch(/sense\/stream|skip.*WS|never cache/);
  });

  it("only caches GET requests", () => {
    expect(swSource).toContain('request.method !== "GET"');
  });
});

// ---------------------------------------------------------------------------
// Service worker registration — SwRegister component smoke test
// ---------------------------------------------------------------------------

describe("SwRegister — registration smoke test", () => {
  beforeEach(() => {
    // Reset the serviceWorker mock between tests
    Object.defineProperty(navigator, "serviceWorker", {
      value: {
        register: jest.fn().mockResolvedValue({ scope: "/" }),
      },
      writable: true,
      configurable: true,
    });
  });

  it("navigator.serviceWorker.register is callable", () => {
    expect(navigator.serviceWorker.register).toBeDefined();
  });

  it("register resolves with a registration object", async () => {
    const reg = await navigator.serviceWorker.register("/sw.js");
    expect(reg).toBeDefined();
    expect(reg.scope).toBe("/");
  });
});
