/**
 * Memory port — append + trajectory queries for the 8-layer memory model
 * (AEON doc §11-12), persisted per entity in the browser.
 *
 * Kept separate from EntityStore because memory grows unbounded while the
 * identity snapshot is small; different eviction/backup strategies apply.
 */

import type { PersistResult } from "./entity-store.js"

export const MEMORY_LAYERS = [
  "working",
  "episodic",
  "semantic",
  "relational",
  "procedural",
  "identity",
  "life_history",
  "world",
] as const

export type MemoryLayer = (typeof MEMORY_LAYERS)[number]

export interface MemoryEntry {
  id?: number
  entity_id: string
  layer: MemoryLayer | string
  content: string
  timestamp: string // ISO-8601
  topics?: string[]
}

export interface MemoryStore {
  /** Append one memory record. Returns its numeric id. */
  append(entry: MemoryEntry): Promise<PersistResult<number>>
  /** Chronological slice for one entity, optionally filtered by layer. */
  timeline(
    entityId: string,
    opts?: { layer?: MemoryLayer | string; limit?: number },
  ): Promise<PersistResult<MemoryEntry[]>>
  /** Trajectory reconstruction: entries whose content/topics match a topic. */
  trajectory(entityId: string, topic: string): Promise<PersistResult<MemoryEntry[]>>
  /** How many memories an entity holds (Memory Depth metric — doc §81). */
  count(entityId: string): Promise<PersistResult<number>>
  /** Forget: delete specific records ("Memory Control" — doc §51). */
  forget(entityId: string, ids: number[]): Promise<PersistResult<number>>
}
