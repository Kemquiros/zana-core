/* aeon-pwa service worker — offline-first.
   Strategy: precache the app shell; network-first with cache fallback for
   everything else. The Aeon's data never leaves IndexedDB, so offline is
   the natural state, not a degraded one. */

const CACHE = "aeon-pwa-v1"
const SHELL = ["./", "./index.html", "./app.js", "./manifest.webmanifest", "./icons/icon-192.png", "./icons/icon-512.png"]

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()),
  )
})

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener("fetch", (event) => {
  const { request } = event
  if (request.method !== "GET") return

  // App shell: cache-first (instant load, works fully offline).
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetched = fetch(request)
        .then((response) => {
          if (response && response.ok && new URL(request.url).origin === location.origin) {
            const copy = response.clone()
            caches.open(CACHE).then((cache) => cache.put(request, copy))
          }
          return response
        })
        .catch(() => cached)
      return cached ?? fetched
    }),
  )
})
