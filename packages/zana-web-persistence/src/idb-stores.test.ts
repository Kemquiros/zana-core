/**
 * TDD RED — EntityStore + MemoryStore over IndexedDB.
 *
 * These tests define the browser persistence contract. They run under Node
 * with fake-indexeddb (same API surface as the browser's native IndexedDB),
 * so the identical suite validates the adapter in CI and in a real browser.
 */

import "fake-indexeddb/auto"
import { afterEach, beforeEach, describe, expect, it } from "vitest"
import { IDBEntityStore, IDBMemoryStore } from "./idb-stores.js"
import type { EntityRecord } from "./ports/entity-store.js"
import { ENTITY_SCHEMA } from "./ports/entity-store.js"

function makeEntity(overrides: Partial<EntityRecord> = {}): EntityRecord {
  return {
    schema: ENTITY_SCHEMA,
    entity_id: "aeon-123",
    kind: "human",
    name: "John",
    created_at: "2026-08-25T00:00:00.000Z",
    personality: { curiosity: 0.9, patience: 0.2 },
    capabilities: ["read_calendar"],
    constraints: {},
    memory: [],
    presence: { public: { bio: "builder" } },
    ...overrides,
  }
}

let store: IDBEntityStore
let memories: IDBMemoryStore

beforeEach(() => {
  store = new IDBEntityStore({ databaseName: "test-aeons" })
  memories = new IDBMemoryStore({ databaseName: "test-aeons" })
})

afterEach(async () => {
  await store.destroyAll()
  await memories.destroyAll()
})

describe("IDBEntityStore", () => {
  it("saves and loads an entity round-trip", async () => {
    const entity = makeEntity()
    const saved = await store.save(entity)
    expect(saved.ok).toBe(true)

    const loaded = await store.load("aeon-123")
    expect(loaded.ok).toBe(true)
    if (loaded.ok) {
      expect(loaded.value).toEqual(entity)
    }
  })

  it("upserts by entity_id without duplicating", async () => {
    await store.save(makeEntity())
    const renamed = makeEntity({ name: "John T." })
    await store.save(renamed)

    const listed = await store.list()
    expect(listed.ok).toBe(true)
    if (listed.ok) {
      expect(listed.value).toHaveLength(1)
      expect(listed.value[0]?.name).toBe("John T.")
    }
  })

  it("rejects records with a foreign schema", async () => {
    const bad = makeEntity({ schema: "other.format/9" as never })
    const result = await store.save(bad)
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.code).toBe("schema_mismatch")
    }
  })

  it("returns not_found for a missing entity", async () => {
    const result = await store.load("ghost")
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.code).toBe("not_found")
    }
  })

  it("deletes an entity and confirms with true", async () => {
    await store.save(makeEntity())
    const deleted = await store.delete("aeon-123")
    expect(deleted.ok).toBe(true)

    const again = await store.delete("aeon-123")
    expect(again.ok).toBe(true)
    if (again.ok) {
      expect(again.value).toBe(false)
    }
    const loaded = await store.load("aeon-123")
    expect(loaded.ok).toBe(false)
  })

  it("lists multiple entities newest-first by created_at", async () => {
    await store.save(makeEntity({ entity_id: "a", created_at: "2026-01-01T00:00:00.000Z" }))
    await store.save(makeEntity({ entity_id: "b", created_at: "2026-06-01T00:00:00.000Z" }))
    await store.save(makeEntity({ entity_id: "c", created_at: "2025-01-01T00:00:00.000Z" }))

    const listed = await store.list()
    expect(listed.ok).toBe(true)
    if (listed.ok) {
      expect(listed.value.map((e) => e.entity_id)).toEqual(["b", "a", "c"])
    }
  })

  it("reports storage usage in bytes", async () => {
    await store.save(makeEntity())
    const usage = await store.usage()
    expect(usage.ok).toBe(true)
    if (usage.ok) {
      expect(usage.value.usedBytes).toBeGreaterThan(0)
    }
  })

  it("survives a full reload of the database connection (persistence)", async () => {
    await store.save(makeEntity())

    // Simulate app restart: brand-new instance, same database.
    const reopened = new IDBEntityStore({ databaseName: "test-aeons" })
    const loaded = await reopened.load("aeon-123")
    expect(loaded.ok).toBe(true)
    if (loaded.ok) {
      expect(loaded.value.name).toBe("John")
    }
  })
})

describe("IDBMemoryStore", () => {
  it("appends entries and returns increasing ids", async () => {
    const e = (content: string, at: string) => ({
      entity_id: "aeon-123",
      layer: "life_history" as const,
      content,
      timestamp: at,
    })
    const r1 = await memories.append(e("Goal: launch product", "2026-01-01T00:00:00.000Z"))
    const r2 = await memories.append(e("Attempted product strategy Y", "2026-06-01T00:00:00.000Z"))
    expect(r1.ok).toBe(true)
    expect(r2.ok).toBe(true)
    if (r1.ok && r2.ok) {
      expect(r2.value).toBeGreaterThan(r1.value)
    }
  })

  it("returns the timeline in chronological order", async () => {
    await memories.append({
      entity_id: "aeon-123",
      layer: "episodic",
      content: "later event",
      timestamp: "2027-01-01T00:00:00.000Z",
    })
    await memories.append({
      entity_id: "aeon-123",
      layer: "episodic",
      content: "earlier event",
      timestamp: "2026-01-01T00:00:00.000Z",
    })

    const tl = await memories.timeline("aeon-123")
    expect(tl.ok).toBe(true)
    if (tl.ok) {
      expect(tl.value[0]?.content).toBe("earlier event")
      expect(tl.value[1]?.content).toBe("later event")
    }
  })

  it("filters the timeline by layer", async () => {
    await memories.append({
      entity_id: "aeon-123",
      layer: "semantic",
      content: "knows fact",
      timestamp: "2026-02-01T00:00:00.000Z",
    })
    await memories.append({
      entity_id: "aeon-123",
      layer: "world",
      content: "world fact",
      timestamp: "2026-03-01T00:00:00.000Z",
    })

    const tl = await memories.timeline("aeon-123", { layer: "semantic" })
    expect(tl.ok).toBe(true)
    if (tl.ok) {
      expect(tl.value).toHaveLength(1)
      expect(tl.value[0]?.layer).toBe("semantic")
    }
  })

  it("reconstructs a trajectory by topic across years", async () => {
    const rows = [
      ["Goal: launch product", "2026-01-01T00:00:00.000Z"],
      ["Attempted product strategy Y", "2026-06-01T00:00:00.000Z"],
      ["Achieved product milestone Z", "2027-02-01T00:00:00.000Z"],
      ["Unrelated note", "2027-03-01T00:00:00.000Z"],
    ] as const
    for (const [content, ts] of rows) {
      await memories.append({
        entity_id: "aeon-123",
        layer: "life_history",
        content,
        timestamp: ts,
      })
    }

    const traj = await memories.trajectory("aeon-123", "product")
    expect(traj.ok).toBe(true)
    if (traj.ok) {
      expect(traj.value).toHaveLength(3)
      const first = traj.value[0]
      const last = traj.value[2]
      expect(first && last ? first.timestamp < last.timestamp : false).toBe(true)
      expect(traj.value.every((m) => m.content.includes("product"))).toBe(true)
    }
  })

  it("isolates memories per entity (multi-entity world)", async () => {
    await memories.append({
      entity_id: "aeon-A",
      layer: "working",
      content: "A thinks",
      timestamp: "2026-01-01T00:00:00.000Z",
    })
    await memories.append({
      entity_id: "aeon-B",
      layer: "working",
      content: "B thinks",
      timestamp: "2026-01-02T00:00:00.000Z",
    })

    const forA = await memories.count("aeon-A")
    const forB = await memories.count("aeon-B")
    expect(forA.ok && forA.value).toBe(1)
    expect(forB.ok && forB.value).toBe(1)
  })

  it("forgets selected records (Memory Control)", async () => {
    const ids: number[] = []
    for (const c of ["keep me", "forget me", "keep me too"]) {
      const r = await memories.append({
        entity_id: "aeon-123",
        layer: "episodic",
        content: c,
        timestamp: "2026-05-01T00:00:00.000Z",
      })
      if (r.ok) ids.push(r.value)
    }

    // forget the middle one
    const forgotten = await memories.forget("aeon-123", [ids[1]!])
    expect(forgotten.ok).toBe(true)

    const count = await memories.count("aeon-123")
    expect(count.ok && count.value).toBe(2)
    const tl = await memories.timeline("aeon-123")
    if (tl.ok) {
      expect(tl.value.every((m) => m.content !== "forget me")).toBe(true)
    }
  })
})
