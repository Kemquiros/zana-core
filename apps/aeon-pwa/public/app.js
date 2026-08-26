/**
 * aeon-pwa app — thin UI over the runtime + persistence ports.
 * All state lives in the user's device (IndexedDB). Zero backend.
 */
import { IDBEntityStore, IDBMemoryStore } from "@vecanova/zana-web-persistence"
import { createAeonSession, InMemoryAeonStore } from "@vecanova/zana-web-runtime"

// ---------------------------------------------------------------------------
// Bridge: adapt the two IDB stores to the runtime's AeonStore port.
// State (personality/goal/stage) rides in the entity record's presence map —
// it IS part of the portable identity, so export/import carries everything.
// ---------------------------------------------------------------------------


class BridgedStore extends InMemoryAeonStore {
  /** @param {{entities: IDBEntityStore, memories: IDBMemoryStore}} idb */
  constructor(idb) {
    super()
    this.idb = idb
    this.entityId = null
  }

  setEntityId(id) {
    this.entityId = id
  }

  async loadState(entityId) {
    const res = await this.idb.entities.load(entityId)
    if (!res.ok) return null
    // Hydrate in-memory mirror with persisted memories so parent class works.
    this.hydrateFrom(res.value)
    return this.states.get(entityId) ?? null
  }

  async saveState(state) {
    await super.saveState(state)
    // Persist as a portable entity snapshot.
    const existing = await this.idb.entities.load(state.entity_id)
    const created_at =
      existing.ok ? existing.value.created_at : new Date().toISOString()
    const memory = (await this.allMemories(state.entity_id))
      .filter((m) => m.layer !== "working")
      .map((m) => ({
        layer: m.layer,
        content: m.content,
        timestamp: m.timestamp,
        topics: m.topics ?? [],
      }))
    await this.idb.entities.save({
      schema: "zana.aeon_entity/1",
      entity_id: state.entity_id,
      kind: "human",
      name: state.name,
      created_at,
      personality: state.personality,
      capabilities: ["remember", "reflect", "set_goal"],
      constraints: {},
      memory,
      presence: {
        private: {
          stage: state.stage,
          goal: state.goal,
        },
      },
    })
  }

  async appendMemory(entry) {
    await super.appendMemory(entry)
    await this.idb.memories.append(entry)
    // Keep the entity snapshot's embedded memory small; full timeline lives
    // in the memory store. Snapshot refresh happens on saveState.
  }

  hydrateFrom(record) {
    // Rebuild the in-memory mirror so reload keeps continuity.
    for (const m of record.memory ?? []) {
      this.memories.push({
        entity_id: record.entity_id,
        layer: m.layer,
        content: m.content,
        timestamp: m.timestamp,
        topics: m.topics ?? [],
      })
    }
    // Restore goal/stage from presence.private into the mirrored state.
    const priv = record.presence?.private ?? {}
    const st = this.states.get(record.entity_id)
    if (!st) {
      this.states.set(record.entity_id, {
        entity_id: record.entity_id,
        name: record.name,
        stage: priv.stage ?? "meeting",
        personality: record.personality ?? {},
        goal: priv.goal ?? null,
      })
    }
  }
}

// ---------------------------------------------------------------------------
// App bootstrap
// ---------------------------------------------------------------------------

const $ = (sel) => document.querySelector(sel)
const chat = $("#chat")
const form = $("#composer")
const input = $("#input")

function addMsg(text, who) {
  const div = document.createElement("div")
  div.className = `msg ${who}`
  div.textContent = text
  chat.appendChild(div)
  chat.scrollTop = chat.scrollHeight
}

async function requestPersistentStorage() {
  try {
    if (navigator.storage?.persist) {
      const granted = await navigator.storage.persist()
      console.info("[aeon] persistent storage:", granted)
    }
  } catch (e) {
    console.warn("[aeon] storage.persist unavailable", e)
  }
}

let session = null

async function boot() {
  const entities = new IDBEntityStore({ databaseName: "zana-aeons" })
  const memories = new IDBMemoryStore({ databaseName: "zana-aeons" })
  const store = new BridgedStore({ entities, memories })

  // Who is this? v0: one person per device, deterministic id. Ask only the name.
  let name = localStorage.getItem("aeon.name")
  if (!name) {
    name = prompt("¿Cómo te llamas? Tu Aeon quiere conocerte.")?.trim()
    if (!name) name = "Amigo"
    localStorage.setItem("aeon.name", name)
  }

  store.setEntityId(`web-${name.toLowerCase()}`)
  ;({ session } = await createAeonSession(store, { name }))

  addMsg(
    `${name}. Estoy aquí.\nCuéntame qué está pasando en tu vida — y dime qué quieres lograr: lo recordaré.`,
    "aeon",
  )

  await requestPersistentStorage()
  registerServiceWorker()
  wireInstallBanner()
}

form.addEventListener("submit", async (e) => {
  e.preventDefault()
  const text = input.value.trim()
  if (!text || !session) return
  input.value = ""
  addMsg(text, "you")
  const reply = await session.say(text)
  addMsg(reply, "aeon")
})

// Privacy as product §50-51: "what my Aeon knows"
$("#btn-knows").addEventListener("click", async () => {
  const list = $("#knows-list")
  list.innerHTML = ""
  const all = await session.recallAll()
  const facts = all.filter((m) => m.layer !== "working")
  if (facts.length === 0) {
    const li = document.createElement("li")
    li.textContent = "Todavía no sé nada sobre ti."
    list.appendChild(li)
  }
  for (const fact of facts.slice().reverse()) {
    const li = document.createElement("li")
    li.textContent = `[${fact.layer}] ${fact.content}`
    const del = document.createElement("button")
    del.textContent = "olvidar"
    del.className = "ghost"
    del.style.marginLeft = "8px"
    del.addEventListener("click", async () => {
      await session.forget(fact.content)
      li.remove()
    })
    li.appendChild(del)
    list.appendChild(li)
  }
  $("#knows-dialog").showModal()
})

$("#btn-close-knows").addEventListener("click", () => $("#knows-dialog").close())

$("#btn-forget-all").addEventListener("click", async () => {
  if (!confirm("¿Borrar TODO lo que tu Aeon sabe? No se puede deshacer.")) return
  const all = await session.recallAll()
  for (const fact of all.filter((m) => m.layer !== "working")) {
    await session.forget(fact.content)
  }
  $("#knows-list").innerHTML = ""
  const li = document.createElement("li")
  li.textContent = "Olvidado todo. Empezamos de cero."
  $("#knows-list").appendChild(li)
})

// Portability §49: export = same file the CLI understands.
$("#btn-export").addEventListener("click", async () => {
  const res = await session.store.idb.entities.load(session.state.entity_id)
  if (!res.ok) return alert("Nada que exportar todavía.")
  const blob = new Blob([JSON.stringify(res.value, null, 2)], {
    type: "application/json",
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `aeon-${session.state.name.toLowerCase()}.json`
  a.click()
  URL.revokeObjectURL(url)
})

// PWA installability
let deferredPrompt = null
function wireInstallBanner() {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault()
    deferredPrompt = e
    $("#install-banner").classList.add("visible")
  })
  $("#btn-install").addEventListener("click", async () => {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    await deferredPrompt.userChoice
    deferredPrompt = null
    $("#install-banner").classList.remove("visible")
  })
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js").catch((err) =>
      console.warn("[aeon] SW registration failed:", err),
    )
  }
}

boot()
