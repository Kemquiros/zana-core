/**
 * TDD RED — the offline conversational runtime ("Meet your Aeon").
 *
 * Product contract (AEON doc §16-19, §45-47, §86):
 *   - A person meets their Aeon in < 3 minutes: name -> talk -> identity
 *     visual -> one goal. No settings screens.
 *   - The Aeon remembers what it is told (layered memory), discovers
 *     patterns (streaks / abandonment / repeated topics), reflects with
 *     trajectories over time, evolves its personality per conversation,
 *     and tracks one active goal.
 *   - Everything works offline with zero LLM calls. Deterministic given
 *     (state, input) — evaluable, not demoable (Constitution §VII).
 */
import { describe, expect, it } from "vitest";
import { createAeonSession, InMemoryAeonStore } from "./runtime.js";
function freshStore() {
    return new InMemoryAeonStore();
}
describe("onboarding", () => {
    it("creates a session from just a name — zero configuration", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "John" });
        expect(session.state.name).toBe("John");
        expect(session.state.stage).toBe("meeting");
    });
    it("records meeting memories and greets personally", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "John" });
        const reply = await session.say("Hola, soy John y quiero ordenar mi vida");
        expect(reply).toContain("John");
        // The first conversation already wrote episodic memory.
        const timeline = await session.recallTimeline();
        expect(timeline.length).toBeGreaterThan(0);
    });
    it("sets the user's first goal conversationally", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "John" });
        await session.say("quiero lanzar mi producto");
        expect(session.state.goal?.text).toContain("lanzar");
        expect(session.state.goal?.createdAt).toBeTruthy();
    });
});
describe("memory layers", () => {
    it("routes identity facts to identity memory", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Ana" });
        await session.say("trabajo como diseñadora de producto");
        const identityFacts = await session.recallLayer("identity");
        expect(identityFacts.some((m) => m.content.includes("diseñadora"))).toBe(true);
    });
    it("answers 'what do you know about me' from semantic+identity memory", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Ana" });
        await session.say("vivo en Medellín");
        await session.say("estudio matemáticas");
        const answer = await session.introspect();
        expect(answer).toContain("Medellín");
        expect(answer).toContain("matemáticas");
    });
    it("forgets on demand (Memory Control §51)", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Ana" });
        await session.say("mi teléfono es 3001234567");
        const before = await session.recallAll();
        expect(before.some((m) => m.content.includes("3001234567"))).toBe(true);
        await session.forget("3001234567");
        const after = await session.recallAll();
        expect(after.every((m) => !m.content.includes("3001234567"))).toBe(true);
    });
});
describe("pattern discovery", () => {
    it("detects repeated topics as an interest pattern", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Lia" });
        await session.say("hoy corrí 5 kilómetros");
        await session.say("mañana corro otra vez");
        await session.say("el running me despeja la mente");
        const patterns = await session.discoverPatterns();
        expect(patterns.some((p) => p.kind === "repeated_topic" && p.topic === "correr")).toBe(true);
    });
    it("detects goal abandonment when days pass without mentions", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Lia" });
        await session.say("quiero aprender piano", { at: "2026-01-01T10:00:00.000Z" });
        // 40 silent days later:
        await session.say("hola de nuevo", { at: "2026-02-10T10:00:00.000Z" });
        const patterns = await session.discoverPatterns();
        const abandoned = patterns.find((p) => p.kind === "goal_stalled");
        expect(abandoned).toBeTruthy();
        if (abandoned && abandoned.kind === "goal_stalled") {
            expect(abandoned.daysSinceLastMention).toBeGreaterThanOrEqual(30);
        }
    });
});
describe("reflection (the WOW moment §19)", () => {
    it("reflects using trajectory + goal state", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Sam" });
        await session.say("quiero escribir un libro", { at: "2026-01-01T10:00:00.000Z" });
        await session.say("escribí el primer capítulo", { at: "2026-01-03T10:00:00.000Z" });
        await session.say("hola que tal", { at: "2026-03-01T10:00:00.000Z" });
        const reflection = await session.reflect({ now: "2026-03-01T10:00:00.000Z" });
        expect(reflection).toContain("libro");
        // It names the stall honestly instead of flattering.
        expect(reflection.match(/pausad|sin mencionar|días/i)).toBeTruthy();
    });
    it("never fabricates facts it was not told", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Sam" });
        const reflection = await session.reflect({ now: "2026-06-01T00:00:00.000Z" });
        // With no history there is nothing to claim — honesty over filler.
        expect(reflection.toLowerCase()).toContain("todavía");
    });
});
describe("personality evolution (§36)", () => {
    it("evolves curiosity after learning-oriented conversations", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Kai" });
        const before = session.state.personality.curiosity ?? 0.5;
        for (const line of [
            "¿por qué ocurre esto?",
            "quiero entender cómo funciona",
            "explícame más",
        ]) {
            await session.say(line);
        }
        const after = session.state.personality.curiosity ?? 0.5;
        expect(after).toBeGreaterThan(before);
        expect(after).toBeLessThanOrEqual(1);
    });
    it("keeps personality within [0,1] after many turns", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Kai" });
        for (let i = 0; i < 50; i++) {
            await session.say(`mensaje número ${i}`);
        }
        for (const value of Object.values(session.state.personality)) {
            expect(value).toBeGreaterThanOrEqual(0);
            expect(value).toBeLessThanOrEqual(1);
        }
    });
});
describe("stage progression (§47 first week arc)", () => {
    it("advances meeting -> knowing -> supporting across interactions", async () => {
        const store = freshStore();
        const { session } = await createAeonSession(store, { name: "Noa" });
        expect(session.state.stage).toBe("meeting");
        await session.say("trabajo en una startup");
        expect(session.state.stage).toBe("knowing");
        await session.say("quiero terminar mi tesis");
        await session.say("avancé un capítulo hoy");
        expect(session.state.stage).toBe("supporting");
    });
});
describe("persistence boundary", () => {
    it("session reloads from store and keeps continuity", async () => {
        const store = freshStore();
        const created = await createAeonSession(store, { name: "Iris" });
        await created.session.say("quiero correr una maratón");
        // Simulate app restart: same store, brand-new session object.
        const reloaded = await createAeonSession(store, { name: "Iris" });
        expect(reloaded.session.state.goal?.text).toContain("maratón");
        const answer = await reloaded.session.introspect();
        expect(answer).toContain("maratón");
    });
});
