// Node test environment: provide a full IndexedDB implementation so the
// same tests run in CI without a real browser. In the browser (aria-ui),
// native indexedDB is used instead — fake-indexeddb is dev-only.
import "fake-indexeddb/auto"
