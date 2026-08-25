/**
 * Entity port — the browser persistence contract for AEON entities.
 *
 * Mirrors the CLI kernel `cli/zana/core/aeon_entity.py` export schema
 * (`zana.aeon_entity/1`) so an Aeon can move between CLI and web without
 * translation loss (AEON doc §49, §79 — portability as trust).
 *
 * Result-typed like @vecanova/persistence: errors are values, no throw
 * as flow control.
 */

export const ENTITY_SCHEMA = "zana.aeon_entity/1" as const

/** Wire shape of an entity — exactly what the CLI kernel emits. */
export interface EntityRecord {
  schema: typeof ENTITY_SCHEMA
  entity_id: string
  kind: string
  name: string
  created_at: string
  personality: Record<string, number>
  capabilities: string[]
  constraints: Record<string, Record<string, unknown>>
  memory: MemoryEntryRecord[]
  presence: Record<string, Record<string, unknown>>
}

export interface MemoryEntryRecord {
  layer: string
  content: string
  timestamp: string
  topics?: string[]
}

export type PersistError =
  | { code: "storage_unavailable"; message: string }
  | { code: "not_found"; message: string }
  | { code: "schema_mismatch"; message: string }
  | { code: "io"; message: string }

export type PersistResult<T> =
  | { ok: true; value: T }
  | { ok: false; error: PersistError }

/** The port. Adapters implement this; the UI never touches IndexedDB. */
export interface EntityStore {
  /** Persist a full entity snapshot (upsert by entity_id). */
  save(entity: EntityRecord): Promise<PersistResult<EntityRecord>>
  /** Load one entity by id. */
  load(entityId: string): Promise<PersistResult<EntityRecord>>
  /** All stored entities, newest-created first. */
  list(): Promise<PersistResult<EntityRecord[]>>
  /** Remove an entity permanently ("puede eliminarlo" — doc §49). */
  delete(entityId: string): Promise<PersistResult<boolean>>
  /** Rough storage usage in bytes (for the privacy dashboard). */
  usage(): Promise<PersistResult<{ usedBytes: number }>>
}
