/**
 * IndexedDB adapters for the EntityStore and MemoryStore ports.
 *
 * Design notes:
 * - One database, two object stores: `entities` (keyed by entity_id) and
 *   `memories` (auto-increment, indexed by [entity_id, timestamp] and
 *   [entity_id, layer]). One DB keeps the privacy story simple: delete the
 *   origin's "zana-aeons" database and the Aeon is gone — no scattered stores.
 * - All writes are transactional.
 * - Errors are values: every method returns PersistResult, never throws
 *   (except documented test helpers).
 * - The wire format is exactly the CLI kernel's export schema
 *   (`zana.aeon_entity/1`), so browser -> CLI portability is byte-compatible.
 */

import { openDB, deleteDB, type IDBPDatabase } from "idb"
import type {
  EntityRecord,
  EntityStore,
  PersistResult,
} from "./ports/entity-store.js"
import { ENTITY_SCHEMA } from "./ports/entity-store.js"
import type {
  MemoryEntry,
  MemoryStore,
} from "./ports/memory-store.js"

const DEFAULT_DB_NAME = "zana-aeons"
const DB_VERSION = 1
const ENTITIES = "entities"
const MEMORIES = "memories"

/**
 * Open range over an [entity_id, timestamp] compound index: every entry of
 * one entity. `["a"] <= key < ["a", \uffff]` matches all keys whose first
 * component is the entity id — the standard IndexedDB prefix-scan idiom.
 */
function entityRange(entityId: string): IDBKeyRange {
  return IDBKeyRange.bound([entityId], [entityId, "\uffff"])
}

function entityLayerRange(entityId: string, layer: string): IDBKeyRange {
  return IDBKeyRange.bound([entityId, layer], [entityId, layer, "\uffff"])
}

export interface StoreOptions {
  databaseName?: string
}

function ok<T>(value: T): PersistResult<T> {
  return { ok: true, value }
}

function fail<T>(code: "io" | "not_found" | "schema_mismatch", message: string): PersistResult<T> {
  return { ok: false, error: { code, message } as never }
}

async function withDb<T>(
  dbName: string,
  fn: (db: IDBPDatabase) => Promise<T>,
): Promise<PersistResult<T>> {
  let db: IDBPDatabase | undefined
  try {
    db = await openDB(dbName, DB_VERSION, {
      upgrade(database) {
        if (!database.objectStoreNames.contains(ENTITIES)) {
          const entities = database.createObjectStore(ENTITIES, {
            keyPath: "entity_id",
          })
          entities.createIndex("by_created_at", "created_at")
        }
        if (!database.objectStoreNames.contains(MEMORIES)) {
          const memories = database.createObjectStore(MEMORIES, {
            keyPath: "id",
            autoIncrement: true,
          })
          memories.createIndex("by_entity_time", ["entity_id", "timestamp"])
          memories.createIndex("by_entity_layer", ["entity_id", "layer"])
        }
      },
    })
    const value = await fn(db)
    return ok(value)
  } catch (err) {
    if (err instanceof NotFoundError) {
      return fail("not_found", err.message)
    }
    return fail("io", err instanceof Error ? err.message : String(err))
  } finally {
    db?.close()
  }
}

class NotFoundError extends Error {}

// ---------------------------------------------------------------------------
// Entities
// ---------------------------------------------------------------------------


export class IDBEntityStore implements EntityStore {
  private readonly dbName: string

  constructor(options: StoreOptions = {}) {
    this.dbName = options.databaseName ?? DEFAULT_DB_NAME
  }

  async save(entity: EntityRecord): Promise<PersistResult<EntityRecord>> {
    if (entity.schema !== ENTITY_SCHEMA) {
      return fail(
        "schema_mismatch",
        `expected schema ${ENTITY_SCHEMA}, got ${String(entity.schema)}`,
      )
    }
    if (!entity.entity_id) {
      return fail("schema_mismatch", "entity_id is required")
    }
    return withDb(this.dbName, async (db) => {
      await db.put(ENTITIES, entity)
      return entity
    })
  }

  async load(entityId: string): Promise<PersistResult<EntityRecord>> {
    return withDb(this.dbName, async (db) => {
      const found = (await db.get(ENTITIES, entityId)) as EntityRecord | undefined
      if (!found) {
        throw new NotFoundError(`entity not found: ${entityId}`)
      }
      return found
    })
  }

  async list(): Promise<PersistResult<EntityRecord[]>> {
    return withDb(this.dbName, async (db) => {
      const all = (await db.getAllFromIndex(
        ENTITIES,
        "by_created_at",
      )) as EntityRecord[]
      // Index yields ascending created_at; product wants newest first.
      return all.reverse()
    })
  }

  async delete(entityId: string): Promise<PersistResult<boolean>> {
    return withDb(this.dbName, async (db) => {
      const existed = (await db.getKey(ENTITIES, entityId)) !== undefined
      if (existed) {
        await db.delete(ENTITIES, entityId)
      }
      return existed
    })
  }

  async usage(): Promise<PersistResult<{ usedBytes: number }>> {
    return withDb(this.dbName, async (db) => {
      const all = (await db.getAll(ENTITIES)) as unknown[]
      const usedBytes = all.reduce<number>(
        (acc, rec) => acc + JSON.stringify(rec).length,
        0,
      )
      return { usedBytes }
    })
  }

  /** Test/maintenance helper: drop the whole database. */
  async destroyAll(): Promise<void> {
    try {
      await deleteDB(this.dbName)
    } catch {
      // best effort — tests tolerate a blocked/missing DB
    }
  }
}

// ---------------------------------------------------------------------------
// Memories
// ---------------------------------------------------------------------------


export class IDBMemoryStore implements MemoryStore {
  private readonly dbName: string

  constructor(options: StoreOptions = {}) {
    this.dbName = options.databaseName ?? DEFAULT_DB_NAME
  }

  async append(entry: MemoryEntry): Promise<PersistResult<number>> {
    return withDb(this.dbName, async (db) => {
      const id = (await db.add(MEMORIES, entry)) as number
      return id
    })
  }

  async timeline(
    entityId: string,
    opts?: { layer?: string; limit?: number },
  ): Promise<PersistResult<MemoryEntry[]>> {
    return withDb(this.dbName, async (db) => {
      const range = opts?.layer
        ? entityLayerRange(entityId, opts.layer)
        : entityRange(entityId)
      const index = opts?.layer ? "by_entity_layer" : "by_entity_time"
      const rows = (await db.getAllFromIndex(
        MEMORIES,
        index,
        range,
      )) as MemoryEntry[]
      const sorted = rows.sort(byTimestamp)
      return opts?.limit ? sorted.slice(0, opts.limit) : sorted
    })
  }

  async trajectory(
    entityId: string,
    topic: string,
  ): Promise<PersistResult<MemoryEntry[]>> {
    return withDb(this.dbName, async (db) => {
      const rows = (await db.getAllFromIndex(
        MEMORIES,
        "by_entity_time",
        entityRange(entityId),
      )) as MemoryEntry[]
      const needle = topic.trim().toLowerCase()
      return rows
        .filter(
          (m) =>
            m.content.toLowerCase().includes(needle) ||
            (m.topics ?? []).some((t) => t.toLowerCase() === needle),
        )
        .sort(byTimestamp)
    })
  }

  async count(entityId: string): Promise<PersistResult<number>> {
    return withDb(this.dbName, async (db) => {
      return db.countFromIndex(MEMORIES, "by_entity_time", entityRange(entityId))
    })
  }

  async forget(entityId: string, ids: number[]): Promise<PersistResult<number>> {
    return withDb(this.dbName, async (db) => {
      let removed = 0
      for (const id of ids) {
        const row = (await db.get(MEMORIES, id)) as MemoryEntry | undefined
        if (row && row.entity_id === entityId) {
          await db.delete(MEMORIES, id)
          removed += 1
        }
      }
      return removed
    })
  }

  /** Test/maintenance helper. */
  async destroyAll(): Promise<void> {
    try {
      await deleteDB(this.dbName)
    } catch {
      // best effort
    }
  }
}

function byTimestamp(a: MemoryEntry, b: MemoryEntry): number {
  return a.timestamp.localeCompare(b.timestamp)
}
