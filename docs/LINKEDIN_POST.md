# LinkedIn Launch Post — ZANA

---

Llevo más de un año construyendo en silencio.

No un chatbot. No un wrapper de GPT-4. Un **runtime cognitivo** — una capa de razonamiento que se mantiene estable mientras el ecosistema de IA cambia cada seis semanas.

Hoy lo hago open source. Se llama **ZANA** — Zero Autonomous Neural Architecture.

---

**El problema que resuelve:**

Cada vez que sale un modelo nuevo, reconstruyes prompts. Cambias SDK. Migras tu memoria. Retrocedes.

Los proveedores mejoran sus modelos. Tu sistema regresa al punto de partida. Eso no es progreso — es dependencia.

ZANA rompe ese ciclo.

---

**Lo que hace diferente:**

🛡️ **Seguridad estructural, no cosmética.** Cada request y respuesta pasa por Armor, un módulo Rust que bloquea PII e inyecciones a 2.1 µs. No es un filtro Python bolteado después. Es una garantía de arquitectura — el LLM nunca ve lo que no debe.

🧠 **Razonamiento neuro-simbólico.** Las salidas del LLM son verificadas por un motor de forward-chaining en Rust (patrón CLIPS). Ninguna deducción sin causa trazable. Ninguna acción sin una regla que la justifique.

🗃️ **Memoria que persiste.** Semántica (ChromaDB) · Episódica (PostgreSQL+pgvector) · Modelo de mundo (Neo4j). Las conversaciones sobreviven cambios de modelo, de proveedor, de año.

🔌 **Plug&Play real.** Claude → GPT → Gemini → Llama local (Ollama) → Groq. Una variable de entorno. Sin cambios de código. ZANA no sabe qué proveedor usas — ni necesita saberlo.

⚔️ **Flota de Aeons.** 8 agentes especializados: Sentinel, Archivist, Analyst, Operator, Herald, Forge, Scholar, Watcher. Cada uno con su propio modelo y toolset. ZANA recomienda cuál usar según el contexto.

🌐 **Corre en todas partes.** Terminal · PWA · Desktop (Linux/Mac/Windows) · Telegram · Slack · Discord. Mismo runtime cognitivo en cada superficie.

---

**ZFI 100/100** — siete pilares medibles, benchmark reproducible incluido.

Respaldado por un **paper técnico de 33 páginas**: arquitectura completa, el operador EML (`eml(x,y) = eˣ − ln(y)`), filtro de Kalman para contexto, y metodología de evaluación.

---

¿Quieres correrlo completamente offline, sin pagar a ningún proveedor?

```
ollama pull llama3.1:8b
ZANA_PRIMARY_MODEL=ollama/llama3.1:8b zana start
```

Listo. IA soberana en tu hardware.

---

🔗 **GitHub:** [github.com/kemquiros/zana-core](https://github.com/kemquiros/zana-core)  
📄 **Paper (PDF):** [Leer el paper →](https://github.com/kemquiros/zana-core/blob/main/docs/paper/zana_paper.pdf)  
⚡ **Instalar en 30s:** `curl -LsSf .../install.sh | sh`

MIT License. Código completo. Construido con honor en Medellín, Colombia.

*JUNTOS HACEMOS TEMBLAR LOS CIELOS.*

---

#AI #OpenSource #CognitiveAI #Rust #Python #NeuralSymbolic #LocalFirstAI #LLM #Ollama #MedellínTech #VECANOVA #AgenticAI
