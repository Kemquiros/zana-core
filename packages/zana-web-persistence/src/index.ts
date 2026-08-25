/**
 * @vecanova/zana-web-persistence — browser persistence for ZANA Aeons.
 *
 * Ports (hexagonal): the UI depends on these interfaces only.
 * Adapters: IndexedDB implementation (`IDBEntityStore`, `IDBMemoryStore`).
 *
 * The entity wire format is byte-compatible with the CLI kernel's
 * `zana.aeon_entity/1` export — an Aeon moves between CLI and browser
 * without translation loss.
 */

export type {
  EntityRecord,
  EntityStore,
  PersistError,
  PersistResult,
} from "./ports/entity-store.js"
export { ENTITY_SCHEMA } from "./ports/entity-store.js"

export type {
  MemoryEntry,
  MemoryStore,
  MemoryLayer,
} from "./ports/memory-store.js"
export { MEMORY_LAYERS } from "./ports/memory-store.js"

export { IDBEntityStore, IDBMemoryStore, type StoreOptions } from "./idb-stores.js"
