/**
 * Offline conversational runtime for ZANA Aeons on the web.
 *
 * Zero LLM dependency: deterministic given (state, input). The Aeon feels
 * alive because it REMEMBERS and NOTICES, not because it improvises —
 * continuity is the product (AEON doc §19, §78).
 *
 * Substrate: @vecanova/zana-web-persistence ports. The runtime never
 * touches IndexedDB directly; InMemoryAeonStore implements the same port
 * for tests, the PWA passes an IDB-backed store.
 */
// ---------------------------------------------------------------------------
// In-memory adapter (tests + SSR-safe default)
// ---------------------------------------------------------------------------
export class InMemoryAeonStore {
    states = new Map();
    memories = [];
    nextId = 1;
    async loadState(entityId) {
        return this.states.get(entityId) ?? null;
    }
    async saveState(state) {
        this.states.set(state.entity_id, structuredClone(state));
    }
    async appendMemory(entry) {
        this.memories.push({ ...entry, id: this.nextId++ });
    }
    async allMemories(entityId) {
        return this.memories.filter((m) => m.entity_id === entityId);
    }
    async deleteMemoriesMatching(entityId, needle) {
        const lower = needle.toLowerCase();
        const before = this.memories.length;
        this.memories = this.memories.filter((m) => m.entity_id !== entityId || !m.content.toLowerCase().includes(lower));
        return before - this.memories.length;
    }
}
// ---------------------------------------------------------------------------
// Language analysis (ES-first, deterministic)
// ---------------------------------------------------------------------------
const STOPWORDS = new Set([
    // Spanish
    "que", "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "a", "en",
    "es", "soy", "estoy", "me", "mi", "mis", "te", "tu", "tus", "se", "lo", "al", "con",
    "para", "por", "como", "más", "mas", "pero", "si", "sí", "no", "hoy", "mañana", "ayer",
    "quiero", "quiero", "puedo", "hay", "fue", "era", "muy", "ya", "esta", "este", "esto",
    "estoy", "estaba", "the", "and", "for", "with", "this", "that", "have", "want", "am",
    "is", "are", "was", "my", "me", "you", "your", "it", "its", "to", "of", "in", "on", "at",
    "i", "a", "an", "be", "been", "was", "were", "do", "does", "did", "not", "but", "very",
    "already", "today", "tomorrow", "yesterday", "again", "more", "about",
]);
const GOAL_TRIGGERS = [
    "quiero", "meta", "objetivo", "planeo", "voy a", "necesito",
    "i want", "my goal", "planning to",
];
const PROGRESS_TRIGGERS = [
    "avancé", "avance", "logré", "terminé", "completé", "escribí", "corrí",
    "practiqué", "estudié", "finished", "completed", "progress",
];
const LEARN_TRIGGERS = ["por qué", "cómo funciona", "explícame", "entender", "why", "how does"];
const IDENTITY_HINTS = [
    "trabajo como", "soy ", "vivo en", "estudio", "trabajo en", "estudio ",
    "i work as", "i live in", "i study",
];
function words(text) {
    return text
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .match(/[a-záéíóúñü]{3,}/g) ?? [];
}
function keywords(text) {
    return words(text).filter((w) => !STOPWORDS.has(w));
}
function stemEs(word) {
    // Light Spanish stemming for topic grouping (correr/corrió/corriendo).
    let w = word
        .replace(/(ando|iendo|ándo|iéndo)$/, "")
        .replace(/(ado|ido|ádo|ído)$/, "")
        .replace(/(ar|er|ir|ár|ér|ír)$/, "");
    if (w.length > 4 && w.endsWith("r"))
        w = w.slice(0, -1);
    // Normalize common irregular stems to a shared prefix.
    for (const [re, base] of IRREGULAR_STEMS) {
        if (re.test(w))
            return base;
    }
    return w;
}
const IRREGULAR_STEMS = [
    [/^corr/, "correr"],
];
function hasAny(text, triggers) {
    const low = text.toLowerCase();
    return triggers.some((t) => low.includes(t));
}
function nowIso(at) {
    return at ?? new Date().toISOString();
}
function daysBetween(aIso, bIso) {
    const a = new Date(aIso).getTime();
    const b = new Date(bIso).getTime();
    return Math.floor(Math.abs(b - a) / 86_400_000);
}
function clamp01(v) {
    return Math.max(0, Math.min(1, v));
}
export class AeonSession {
    state;
    store;
    constructor(store, state) {
        this.store = store;
        this.state = state;
    }
    get entityId() {
        return this.state.entity_id;
    }
    /**
     * One conversation turn: memory write -> state update -> reply.
     * Returns what the Aeon says. Deterministic given (state, input).
     */
    async say(input, opts = {}) {
        const at = nowIso(opts.at);
        const text = input.trim();
        await this.classifyAndStore(text, at);
        this.maybeSetGoal(text, at);
        this.maybeTrackGoalMention(text, at);
        this.evolvePersonality(text);
        this.advanceStage();
        await this.store.saveState(this.state);
        if (!this.state.goal && GOAL_TRIGGERS.some((t) => text.toLowerCase().includes(t)) === false) {
            return this.replyFor(text);
        }
        return this.replyFor(text);
    }
    /** Layered recall. */
    async recallLayer(layer) {
        const all = await this.store.allMemories(this.state.entity_id);
        return all.filter((m) => m.layer === layer);
    }
    async recallTimeline() {
        const all = await this.store.allMemories(this.state.entity_id);
        return all.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    }
    async recallAll() {
        return this.recallTimeline();
    }
    /** Privacy dashboard content: everything the Aeon knows, human-readable. */
    async introspect() {
        const facts = await this.recallLayer("identity");
        const semantics = await this.recallLayer("semantic");
        const lines = [
            ...facts.map((m) => `• ${capitalize(m.content)}`),
            ...semantics.map((m) => `• ${capitalize(m.content)}`),
        ];
        if (this.state.goal) {
            lines.push(`• Tu meta actual: ${this.state.goal.text}`);
        }
        if (lines.length === 0) {
            return "Todavía no sé mucho sobre ti. Cuéntame lo que quieras que recuerde.";
        }
        return `Esto es lo que sé de ti:\n${lines.join("\n")}`;
    }
    /** Memory Control §51: forget anything containing a term. */
    async forget(term) {
        return this.store.deleteMemoriesMatching(this.state.entity_id, term);
    }
    /** Pattern discovery over the full timeline (§18 discover). */
    async discoverPatterns() {
        const timeline = await this.recallTimeline();
        const patterns = [];
        // repeated_topic: same stemmed keyword >= 3 mentions
        const counts = new Map();
        for (const m of timeline) {
            for (const w of keywords(m.content)) {
                const key = stemEs(w);
                const prev = counts.get(key) ?? { count: 0, last: m.timestamp };
                counts.set(key, { count: prev.count + 1, last: m.timestamp });
            }
        }
        for (const [topic, info] of counts) {
            if (info.count >= 3) {
                patterns.push({
                    kind: "repeated_topic",
                    topic,
                    occurrences: info.count,
                    detail: `"${topic}" apareció ${info.count} veces`,
                });
            }
        }
        // goal_stalled: goal exists, no mention in >= 30 days
        if (this.state.goal) {
            const since = daysBetween(this.state.goal.lastMentionAt, nowIso());
            if (since >= 30) {
                patterns.push({
                    kind: "goal_stalled",
                    daysSinceLastMention: since,
                    detail: `Tu meta "${this.state.goal.text}" lleva ${since} días sin mencionarse`,
                });
            }
        }
        // learning_streak: curiosity high + learning verbs present recently
        if ((this.state.personality.curiosity ?? 0) > 0.6 && timeline.length >= 3) {
            patterns.push({
                kind: "learning_streak",
                detail: "Estás en racha de curiosidad: varias conversaciones exploratorias seguidas",
            });
        }
        return patterns;
    }
    /**
     * Weekly reflection (§19 WOW moment). Honest, trajectory-based:
     * names what was said, what advanced, and what stalled. Never invents.
     */
    async reflect(opts = {}) {
        const timeline = await this.recallTimeline();
        if (timeline.length === 0) {
            return "Todavía no tenemos historia juntos. Cuando me cuentes cosas, podré reflexionar sobre tu camino.";
        }
        const parts = [];
        const first = timeline[0];
        const spanDays = daysBetween(first.timestamp, nowIso(opts.now));
        if (this.state.goal) {
            const goalMentions = timeline.filter((m) => m.layer !== "identity" &&
                sharesTopic(m.content, this.state.goal?.text ?? ""));
            const lastGoalMention = goalMentions.length > 0
                ? goalMentions[goalMentions.length - 1].timestamp
                : this.state.goal.createdAt;
            const silentDays = daysBetween(lastGoalMention, nowIso(opts.now));
            const progressed = goalMentions.some((m) => hasAny(m.content, PROGRESS_TRIGGERS));
            parts.push(`Tu meta "${this.state.goal.text}" empezó el ${dateShort(this.state.goal.createdAt)}.`);
            if (progressed && silentDays < 14) {
                parts.push("Has avanzado en ella y sigues activo: eso es exactamente la continuidad que buscamos.");
            }
            else if (silentDays >= 30) {
                parts.push(`Llevas ${silentDays} días sin mencionarla. No creo que sea falta de disciplina: quizá hay una restricción que no hemos identificado.`);
            }
            else {
                parts.push("Sigues cerca de ella; retomémosla.");
            }
        }
        else if (spanDays > 7) {
            parts.push(`Llevamos ${spanDays} días conversando y todavía no has fijado una meta. ¿Cuál sería la tuya?`);
        }
        const topTopics = topKeywords(timeline.map((m) => m.content), 3);
        if (topTopics.length > 0) {
            parts.push(`Los temas que más se repiten contigo: ${topTopics.join(", ")}.`);
        }
        if (parts.length === 0) {
            return "Todavía no tengo suficiente historia para reflexionar.";
        }
        return parts.join(" ");
    }
    // -- internals ----------------------------------------------------------
    async classifyAndStore(text, at) {
        let layer = "episodic";
        if (IDENTITY_HINTS.some((h) => text.toLowerCase().includes(h))) {
            layer = "identity";
        }
        else if (hasAny(text, PROGRESS_TRIGGERS)) {
            layer = "semantic";
        }
        await this.store.appendMemory({
            entity_id: this.state.entity_id,
            layer,
            content: text,
            timestamp: at,
            topics: keywords(text).slice(0, 6),
        });
        // working memory: the immediate context (latest turn)
        await this.store.appendMemory({
            entity_id: this.state.entity_id,
            layer: "working",
            content: `[turn] ${text}`,
            timestamp: at,
            topics: [],
        });
    }
    maybeSetGoal(text, at) {
        if (this.state.goal)
            return;
        if (!hasAny(text, GOAL_TRIGGERS))
            return;
        const kw = keywords(text);
        if (kw.length === 0)
            return;
        this.state.goal = {
            text: extractGoalText(text),
            createdAt: at,
            lastMentionAt: at,
        };
    }
    maybeTrackGoalMention(text, at) {
        if (!this.state.goal)
            return;
        if (sharesTopic(text, this.state.goal.text)) {
            this.state.goal.lastMentionAt = at;
        }
    }
    evolvePersonality(text) {
        const p = this.state.personality;
        if (hasAny(text, LEARN_TRIGGERS)) {
            p.curiosity = clamp01((p.curiosity ?? 0.5) + 0.05);
        }
        if (hasAny(text, PROGRESS_TRIGGERS)) {
            p.proactivity = clamp01((p.proactivity ?? 0.5) + 0.04);
            p.patience = clamp01((p.patience ?? 0.5) + 0.02);
        }
        if (text.includes("?")) {
            p.curiosity = clamp01((p.curiosity ?? 0.5) + 0.02);
        }
        if (hasAny(text, GOAL_TRIGGERS)) {
            p.assertiveness = clamp01((p.assertiveness ?? 0.5) + 0.03);
        }
    }
    advanceStage() {
        if (this.state.stage === "meeting") {
            this.state.stage = "knowing";
            return;
        }
        if (this.state.stage === "knowing" && this.state.goal) {
            this.state.stage = "supporting";
        }
    }
    replyFor(text) {
        const name = this.state.name;
        if (hasAny(text, PROGRESS_TRIGGERS)) {
            const goalRef = this.state.goal ? ` sobre "${this.state.goal.text}"` : "";
            return `Anotado${goalRef}, ${name}. Cada paso así es la prueba de continuidad: yo sí me acuerdo.`;
        }
        if (hasAny(text, GOAL_TRIGGERS) && this.state.goal) {
            return `Meta guardada, ${name}: "${this.state.goal.text}". Voy a recordar cada avance y también los silencios.`;
        }
        if (IDENTITY_HINTS.some((h) => text.toLowerCase().includes(h))) {
            return `Gracias por contarme, ${name}. Eso ya forma parte de quién eres para mí.`;
        }
        if (text.includes("?")) {
            return `Buena pregunta, ${name}. Mientras aprendo a responder mejor, lo importante es que tus preguntas ya me dicen quién eres.`;
        }
        return `Te escucho, ${name}. Sigue contándome: cuanto más me des, más te reconozco.`;
    }
}
// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------
export async function createAeonSession(store, opts) {
    // Deterministic entity id per person+name so reload finds the same Aeon.
    const entityId = opts.entityId ?? `web-${opts.name.toLowerCase().trim()}`;
    const existing = await store.loadState(entityId);
    const state = existing ??
        {
            entity_id: entityId,
            name: opts.name,
            stage: "meeting",
            personality: defaultPersonality(),
            goal: null,
        };
    const session = new AeonSession(store, state);
    if (!existing) {
        // The greeting is the Aeon's own first memory, not a user turn:
        // it must not advance the relationship stage.
        const initialStage = state.stage;
        await session.say(`Hola, soy ${opts.name}`, {
            at: new Date().toISOString(),
        });
        state.stage = initialStage;
        await store.saveState(state);
    }
    return { session };
}
function defaultPersonality() {
    return {
        curiosity: 0.6,
        risk: 0.4,
        empathy: 0.7,
        assertiveness: 0.4,
        sociability: 0.6,
        patience: 0.5,
        creativity: 0.55,
        humor: 0.45,
        formality: 0.35,
        proactivity: 0.5,
    };
}
function extractGoalText(text) {
    // Keep it short and quotable: strip trigger verb, cap length.
    const cleaned = text
        .replace(/^(quiero|necesito|voy a|planeo|mi meta es|my goal is)\s+/i, "")
        .replace(/[.!?]+$/, "")
        .trim();
    return cleaned.length > 80 ? `${cleaned.slice(0, 77)}...` : cleaned || text;
}
function sharesTopic(a, b) {
    const ka = new Set(keywords(a).map(stemEs));
    const kb = keywords(b).map(stemEs);
    return kb.some((w) => ka.has(w));
}
function topKeywords(contents, n) {
    const counts = new Map();
    for (const c of contents) {
        for (const w of keywords(c)) {
            const k = stemEs(w);
            counts.set(k, (counts.get(k) ?? 0) + 1);
        }
    }
    return [...counts.entries()]
        .filter(([, c]) => c >= 2)
        .sort((a, b) => b[1] - a[1])
        .slice(0, n)
        .map(([k]) => k);
}
function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}
function dateShort(iso) {
    return iso.slice(0, 10);
}
