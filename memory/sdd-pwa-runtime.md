# SDD: AEON PWA Runtime — `@vecanova/zana-web-runtime` v0.1.0 + `apps/aeon-pwa`

> Contexto → Decisión → Alternativas → Consecuencias.
> Tercera rebanada del producto AEON: PWA instalable "Meet your Aeon" (doc §16-19, §45-47, §55, §59, §86, §91).

## Contexto

El doc AEON define dos productos sobre la misma ontología (§91):
- **CLI** = soberano, power-user, local-first, Postgres sync para Tier 1.
- **PWA** = adopción masiva, instalable, offline, cero configuración, onboarding <3 min.

La Fase A del roadmap interno exige tracción orgánica. Sin PWA no hay canal de
entrada para usuarios no técnicos. El CLI ya existe (v3.15+), la persistencia
navegador ya existe (PR #86). Lo que falta es el **runtime conversacional** y
el **shell estático** que los conecta.

## Decisión

Dos artefactos nuevos en el monorepo:

### 1. `@vecanova/zana-web-runtime` (packages/zana-web-runtime)

Runtime offline, determinista, **zero LLM**. El Aeon "se siente vivo" porque
RECUERDA y NOTA (§78), no porque improvise.

**API pública (puertos hexagonales, espejo de @vecanova/persistence):**

```ts
interface AeonStore {
  loadState(entityId): Promise<AeonState | null>
  saveState(state): Promise<void>
  appendMemory(entry): Promise<void>
  allMemories(entityId): Promise<MemoryEntryLike[]>
  deleteMemoriesMatching(entityId, needle): Promise<number>
}
```

**Sesión (`AeonSession`):**
- `say(input, {at?})` → respuesta + escritura memoria + actualización estado
- `recallLayer(layer)` / `recallTimeline()` / `recallAll()` / `introspect()`
- `forget(term)` — Memory Control §51
- `discoverPatterns()` → repeated_topic / goal_stalled / learning_streak
- `reflect({now?})` — WOW moment §19: honesto, basado en trayectoria
- Estado persistido: `AeonState` { entity_id, name, stage, personality[10], goal }

**Decisiones de diseño:**
- **Determinista**: misma (state, input) → misma salida. Testable, no demoable.
- **ES-first**: tokenización simple, stopwords ES/EN, stemming ligero (correr/corrió/corriendo → "correr").
- **Clamped [0,1]**: 10 rasgos (curiosity, risk, empathy, assertiveness, sociability, patience, creativity, humor, formality, proactivity).
- **Stages**: meeting → knowing (1er dato identidad) → supporting (meta existe).
- **Sin throw en control flow**: errores como valores en stores; sesión no falla.

### 2. `apps/aeon-pwa` (apps/aeon-pwa)

Shell estático, sin framework. Build = esbuild IIFE bundle.

**Arquitectura:**
```
index.html (app shell)
  → app.js (UI + bridge)
      → @vecanova/zana-web-runtime (AeonSession)
      → @vecanova/zana-web-persistence (IDBEntityStore, IDBMemoryStore)
          → IndexedDB "zana-aeons"
```

**Bridge (`BridgedStore extends InMemoryAeonStore`):**
- Hidrata in-memory store desde entity record al cargar
- `saveState` persiste snapshot completo (incluye goal/stage/personality en `presence.private`)
- `appendMemory` escribe también a IDBMemoryStore
- Export = entidad portable completa (schema `zana.aeon_entity/1`)

**PWA checklist:**
- manifest.webmanifest válido (name, short_name, icons 192/512 maskable, display: standalone)
- Service worker: precache shell, network-first con cache fallback, version bump por build
- navigator.storage.persist() solicitado en boot
- Install banner antes del `beforeinstallprompt`
- Íconos generados programáticamente (gradiente sigil Aeon)

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Framework (React/Svelte/Vue) | Bundle >100KB, build tooling, hidratación. El caso de uso es una conversación + dashboard. Vanilla + esbuild IIFE = 30KB gz, cero dependencias runtime. |
| LLM integrado desde v0 | Contradice Fase A sin servidor + soberanía-by-default. LLM = coste recurrente, latencia, dependencia de red. v0 demuestra que la *personalidad* (recordar, notar, reflexionar) basta para el primer encuentro. LLM = adaptador enchufable futuro. |
| Backend para sync | La tesis del producto es **soberanía**: el Aeon vive en TU dispositivo. Postgres sync = Tier 1 premium (monetización), no bloqueante para la PWA gratuita. |
| IndexedDB crudo en la UI | Ya resuelto en PR #86: puertos hexagonales. La UI depende del contrato (`AeonStore`), no de la implementación. Permite test con InMemoryAeonStore y swap a OPFS/sqlite-wasm futuro sin tocar runtime. |

## Consecuencias

**Positivas:**
- **Producto real**: cualquiera abre la URL, instala, tiene su Aeon en <3 min. Offline. Sin email.
- **Categoría creada**: "Digital Entity Platform" (§91) — el Aeon no es un chatbot, es una entidad digital persistente con identidad, memoria longitudinal, agencia autorizada.
- **Portabilidad real**: export PWA importa en CLI y viceversa (byte-identical `zana.aeon_entity/1`).
- **Extensible**: runtime es puro TS; LLM adapter, Aeon↔Aeon protocol, Postgres sync se enchufan detrás de los mismos puertos.

**Deuda registrada (en kanban):**
1. Cifrado en reposo del store IDB (CLI ya cifra `.zaeon.enc` con AES-GCM; patrón reutilizable).
2. `navigator.storage.persist()` ya solicitado — monitorizar eviction en analytics.
3. OPFS/sqlite-wasm detrás de los mismos puertos cuando haga falta búsqueda semántica local (FTS5).
4. Wiring real en `aria-ui` (los puertos están listos).
5. Protocolo Aeon↔Aeon (§59-60) — el mecanismo viral del doc.
6. Deploy estático a vercel/gh-pages + dominio `aeon.vecanova.com` o similar.
7. Share card visual (imagen OG dinámica con el sigil + nombre + meta) — objeto social §59.

## Evidencia

- TDD: 14 tests escritos primero (`runtime.test.ts`), luego implementación (`runtime.ts`) → 14/14 green.
- Suite total: 28 tests (14 runtime + 14 persistence) green.
- TypeScript strict: `tsc --noEmit` limpio en ambos paquetes.
- Build: `dist/runtime.js` + `dist/runtime.d.ts` + `dist/index.js` + `dist/index.d.ts` emitidos.
- CLI suite spot-check: `test_memory_crud.py + test_aeon_entity.py` = 74 passed.
- CI verde: Code Quality + Python Tests + Rust.
- PWA build: `dist/` con `index.html`, `app.js` (IIFE bundle), `manifest.webmanifest`, `sw.js`, `icons/`, `robots.txt` — archivos estáticos puros.