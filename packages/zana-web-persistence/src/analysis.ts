/**
 * zana-web-persistence — browser-side persistence for ZANA Aeons.
 *
 * Analysis record (2026-08-25): CAN it be done in the browser, and SHOULD it?
 *
 * CAN — yes, three viable stacks:
 *   1. IndexedDB (via `idb`) — native, universal (Safari 14+/Chrome/FF),
 *      async, ~50-500MB quota, no WASM, works in SharedArrayBuffer-less
 *      contexts and inside Tauri webviews. Chosen.
 *   2. OPFS + sqlite-wasm (@sqlite.org/sqlite-wasm) — real SQLite with
 *      sync access handles; requires COOP/COEP headers on the origin,
 *      heavier bundle (~1MB wasm), Safari support only recent. Deferred:
 *      right fit when we need real SQL joins / FTS5 in-browser.
 *   3. sql.js — wasm SQLite but in-memory only; persistence means manual
 *      full-dump export into IndexedDB anyway. Strictly dominated by 1+2.
 *
 * SHOULD — yes, for these product reasons (AEON doc §30-31, §49, §77):
 *   - Sovereign-by-default is the brand: the Aeon's identity/memory living
 *     in the user's own browser storage is the same thesis as local-first
 *     CLI. The browser IS another personal device.
 *   - Persistence (doc §31): "si sales, el mundo continúa" — the entity
 *     must survive reloads without any backend.
 *   - Portability (doc §49): export/import round-trip is a product promise;
 *     the adapter serializes to the same aeon_entity JSON schema the CLI
 *     kernel emits (`zana.aeon_entity/1`), so an Aeon can move
 *     browser -> file -> CLI without translation loss.
 *   - Zero-backend launch: Fase A has no server budget; IndexedDB needs none.
 *
 * NOT solved here (recorded as known limits):
 *   - Eviction: browsers may evict non-persistent storage under pressure.
 *     Mitigation: request `navigator.storage.persist()` at app level.
 *   - Multi-tab writes: single-writer assumption per origin; a Web Locks
 *     wrapper is future work if aria-ui ever multi-tabs heavily.
 */

export const SCHEMA = "zana.aeon_entity/1" as const
