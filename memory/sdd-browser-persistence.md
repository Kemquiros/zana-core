# SDD: AEON Browser Persistence — `@vecanova/zana-web-persistence` v0.1.0

> Contexto → Decisión → Alternativas → Consecuencias.
> Siguiente rebanada del producto AEON tras el kernel v0 (PR #85).

## Contexto

El doc AEON v1.0 exige tres propiedades que el CLI solo cumple en desktop:

1. **Persistencia** (§31): "si sales, el mundo continúa" — la entidad sobrevive
   al cierre sin backend.
2. **Accesibilidad universal** (§30): web/mobile sin hardware especial ni
   instalación — "el usuario no debería necesitar GPU ni PC gamer".
3. **Portabilidad** (§49, §79): export/import como promesa de confianza.

La Fase A del roadmap interno no tiene presupuesto de servidor: cualquier
solución con backend queda descartada para el MVP. El consumidor natural es
aria-ui (PWA/Tauri ya presente en el repo).

## Decisión

Nuevo paquete TS en el monorepo: `packages/zana-web-persistence`.

**Stack elegido: IndexedDB vía `idb` (~1.2KB gz).**

| Criterio | IndexedDB (idb) | OPFS + sqlite-wasm | sql.js |
|---|---|---|---|
| Soporte | Universal (Safari 14+) | COOP/COEP headers obligatorios; Safari reciente | Universal |
| Persistencia | Nativa, automática | Nativa (sync handles) | Solo memoria; export manual a IDB igualmente |
| Bundle | ~1KB | ~1MB WASM | ~1MB WASM |
| SQL real / FTS5 | No | Sí | Sí |
| Riesgo PWA hoy | Bajo | Medio-alto | Dominado por las otras dos |

Se elige IndexedDB porque el caso de uso (snapshot de identidad + timeline
de memoria por entidad) no necesita joins ni FTS5 en cliente; si más adelante
hace falta búsqueda semántica local, la migración natural es OPFS+sqlite-wasm
detrás de los MISMOS puertos.

**Arquitectura hexagonal**, espejo del patrón de `@vecanova/persistence`
(Turso) ya establecido por el workspace:

- Puertos puros (`src/ports/`): `EntityStore`, `MemoryStore`. Result-type
  (errores son valores, sin throw como control de flujo).
- Adaptador único (`src/idb-stores.ts`): una base de datos `zana-aeons`,
  dos object stores (`entities` keyed por entity_id, `memories`
  autoincremental con índices compuestos `[entity_id, timestamp]` y
  `[entity_id, layer]`). Una sola DB = borrarla borra el Aeon entero:
  historia de privacidad simple y verificable.
- Wire format: exactamente `zana.aeon_entity/1` del kernel CLI. Sin capa de
  traducción = portabilidad byte-compatible CLI ↔ navegador.
- Tests corren en Node con `fake-indexeddb` (misma superficie API que
  IndexedDB nativo): la misma suite valida CI y navegador.

## Evidencia

- TDD RED→GREEN: 14 tests escritos antes del adaptador (`idb-stores.test.ts`).
- Gates: `vitest run` 14/14 ✓ · `tsc --noEmit` limpio ✓ · `npm run build`
  genera dist+declaraciones ✓ · suite CLI intacta (74 tests de memory+entity
  spot-checked) ✓
- **Round-trip cross-boundary verificado**: kernel Python exporta JSON →
  adaptador TS lo importa a IndexedDB → se recupera byte-idéntico, con
  trayectoria temporal reconstruida en el store de memorias
  (2026-01-01 → 2027-02-01 para topic "product").

## Alternativas descartadas

- **Backend Postgres desde el día 1**: contradice soberanía-by-default y la
  Fase A sin servidor; la persistencia Postgres del CLI (identity_schema.sql)
  sigue siendo el camino para sync multi-device premium (Tier 1).
- **localStorage**: límite ~5MB síncrono, sin índices, sin consultas —
  insuficiente para memoria longitudinal.
- **sqlite-wasm inmediato**: paga 1MB de bundle + headers COOP/COEP antes de
  necesitar SQL real. Registrado como evolución detrás de los mismos puertos.

## Consecuencias

**Positivas:** el Aeon existe ahora en el navegador — la unidad fundamental
del mundo AEON corre en el dispositivo más ubicuo. El MVP §86 del doc
(Create Identity, Talk, Remember, Reflect...) tiene su substrato persistente
sin backend. aria-ui puede enchufar los puertos directamente.

**Deuda registrada:**
1. `navigator.storage.persist()` a nivel app contra eviction del navegador.
2. Web Locks si aria-ui llega a multi-tab con escrituras concurrentes.
3. Cifrado en reposo dentro de IDB (el CLI cifra .zaeon.enc; el browser aún
   no) — siguiente iteración, reutilizando el patrón AES-GCM del kernel.
4. Adaptador OPFS/sqlite-wasm cuando haga falta FTS5/búsqueda semántica local.
5. Integración real en aria-ui (los puertos están listos; falta el wiring).
