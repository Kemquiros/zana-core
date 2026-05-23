"""
zsm_engine.py — ZSM Symbolic NLU Engine

6-stage pipeline:
  [1] Normalize   — unicode NFC, lowercase, strip punctuation
  [2] Tokenize    — whitespace split + basic Spanish/English stemming
  [3] Expand      — synonym table ES+EN (~150 pairs)
  [4] Score       — Jaccard + difflib fuzzy per intent candidate
  [5] Extract     — entities: paths, URLs, emails, numbers
  [6] Context     — session context adjusts scores ±0.10
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import deque

# ── [1] Normalize ─────────────────────────────────────────────────────────────


def normalize(text: str) -> str:
    """Unicode NFC, lowercase, strip unwanted punctuation, collapse spaces."""
    text = unicodedata.normalize("NFC", text)
    text = text.lower().strip()
    # Remove punctuation EXCEPT chars needed for paths/emails/URLs
    # Keep: / . ~ - _ @ + (and space); + is used in email local parts
    text = re.sub(r"[^\w\s/.\~\-_@+]", " ", text, flags=re.UNICODE)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── [2] Tokenize ──────────────────────────────────────────────────────────────

# Suffixes to strip (ordered longest-first to avoid partial matches)
_STEM_SUFFIXES = re.compile(
    r"(ando|iendo|ción|ciones|mente|ados|adas|idos|idas|ado|ada|ar|er|ir|es|s)$"
)


def _stem(token: str) -> str:
    """Very lightweight Spanish/English suffix stripping."""
    m = _STEM_SUFFIXES.search(token)
    if m:
        candidate = token[: m.start()]
        if len(candidate) > 3:
            return candidate
    return token


def tokenize(text: str) -> list[str]:
    """Split on whitespace, apply basic desinflection, filter short tokens."""
    raw = text.split()
    result: list[str] = []
    for tok in raw:
        stemmed = _stem(tok)
        if len(stemmed) >= 2:
            result.append(stemmed)
    return result


# ── [3] Synonyms & Expand ─────────────────────────────────────────────────────

_SYNONYMS: dict[str, list[str]] = {
    # --- file ops ---
    "lista": ["muestra", "ver", "show", "display", "listar", "listado", "enseña"],
    "archivo": ["fichero", "file", "documento", "doc", "texto"],
    "carpeta": ["directorio", "folder", "directory", "dir"],
    "busca": [
        "encuentra",
        "find",
        "search",
        "buscar",
        "hallar",
        "localiza",
        "cherche",
        "cerca",
        "suche",
    ],
    "copia": ["copy", "duplica", "cp"],
    "mueve": ["move", "mv", "traslada", "desplaza"],
    "crea": ["create", "nuevo", "new", "make", "mkdir", "nuevo"],
    "borra": ["elimina", "delete", "rm", "remove", "quita", "suprime"],
    "abre": ["open", "abre", "leer", "read"],
    "guarda": ["save", "store", "almacena", "keep"],
    "renombra": ["rename", "mv"],
    # --- memory ---
    "recuerda": [
        "remember",
        "guarda",
        "save",
        "almacena",
        "memoria",
        "lembra",
        "souviens",
        "ricorda",
        "erinnere",
    ],
    "olvida": ["forget", "elimina", "delete", "olvidar"],
    "memoria": ["memory", "recuerdo", "historico", "history"],
    # --- wisdom ---
    "aprende": ["learn", "absorbe", "captura", "regla", "rule", "aprender"],
    "propone": ["propose", "sugiere", "suggest", "proponer"],
    "aprueba": ["approve", "acepta", "accept", "aprobar"],
    "regla": ["rule", "norma", "ley", "policy"],
    "sabiduria": ["wisdom", "conocimiento", "knowledge"],
    # --- shell ---
    "ejecuta": ["run", "execute", "corre", "lanza", "launch", "ejecutar", "correr"],
    "proceso": ["process", "servicio", "service", "daemon"],
    "espacio": ["space", "disco", "disk", "uso", "storage"],
    "puerto": ["port", "socket", "conexion"],
    "comando": ["command", "cmd", "orden"],
    "terminal": ["shell", "bash", "zsh", "consola", "console"],
    "linea": ["line", "row", "entrada"],
    "cuenta": ["count", "contar", "numera"],
    # --- web ---
    "internet": ["web", "online", "red", "network", "navegador", "browser"],
    "googlea": ["search", "busca", "duckduckgo", "bing"],
    "descarga": ["download", "bajar", "fetch"],
    "sitio": ["site", "pagina", "page", "url", "link"],
    # --- chat / companion ---
    "pregunta": ["ask", "consulta", "query", "dime", "explica", "explain"],
    "responde": ["answer", "contesta", "reply", "respuesta"],
    "hola": ["hello", "hi", "hey", "buenas", "saludo", "greet"],
    "adios": ["bye", "goodbye", "hasta", "chao", "ciao"],
    # --- sync ---
    "sincroniza": ["sync", "actualiza", "update", "pull", "push", "sincronizar"],
    "actualiza": ["update", "refresh", "renovar"],
    # --- sentinel / security ---
    "seguridad": [
        "security",
        "amenaza",
        "threat",
        "alerta",
        "alert",
        "proteccion",
        "protection",
    ],
    "eventos": ["events", "log", "registro", "audit", "bitacora"],
    "amenaza": ["threat", "riesgo", "risk", "peligro", "danger"],
    "firewall": ["cortafuegos", "bloqueo", "block"],
    # --- aeon / network ---
    "conecta": ["connect", "link", "enlaza", "peer", "conectar"],
    "enjambre": ["swarm", "network", "red", "peers", "malla"],
    "broadcast": ["transmite", "envia", "send", "difunde", "difundir"],
    "ping": ["latencia", "latency", "alcance", "reachable"],
    "nodo": ["node", "peer", "host", "servidor"],
    # --- herald / notifications ---
    "notifica": ["notify", "alerta", "avisa", "mensaje", "message", "aviso"],
    "canal": ["channel", "slack", "canal", "grupo"],
    "correo": ["email", "mail", "envia", "send"],
    "slack": ["canal", "workspace", "equipo", "team"],
    # --- skill ---
    "habilidad": ["skill", "capacidad", "plugin", "modulo", "extension"],
    "instala": ["install", "adopt", "anada", "agrega", "add", "instalar"],
    "publica": ["publish", "comparte", "share", "release", "publicar"],
    "flujo": ["workflow", "pipeline", "automatiza", "automate"],
    # --- time ---
    "hora": ["time", "reloj", "clock", "cuando"],
    "fecha": ["date", "dia", "day", "hoy", "today", "ahora", "now"],
    "tiempo": ["time", "momento", "instante"],
    # --- economy / finance ---
    "gaste": ["spent", "pague", "paid", "gasto", "expense"],
    "compre": ["bought", "adquiri", "purchase", "comprar"],
    "presupuesto": ["budget", "plan", "limite", "limit"],
    "ingreso": ["income", "earned", "revenue", "salary", "salario"],
    "gasto": ["expense", "cost", "costo", "precio", "price"],
    # --- language learning ---
    "traduce": ["translate", "traducir", "traduction", "vertaling"],
    "idioma": ["language", "lengua", "tongue", "lingua"],
    "palabra": ["word", "termino", "term", "vocabulario", "vocab"],
    "ensenanza": ["lesson", "clase", "class", "leccion", "teach"],
    # --- cooking ---
    "receta": ["recipe", "preparacion", "preparation", "formula"],
    "cocina": ["cook", "kitchen", "cuisine", "cocinar"],
    "ingrediente": ["ingredient", "componente", "elemento"],
    "prepara": ["prepare", "hacer", "make", "elaborar"],
    # --- vault / notes ---
    "nota": ["note", "apunte", "memo", "anotacion"],
    "obsidian": ["vault", "cofre", "boveda", "repositorio"],
    "documento": ["document", "doc", "archivo", "paper"],
    # --- math ---
    "calcula": ["calculate", "compute", "suma", "multiplica"],
    "resultado": ["result", "total", "suma", "output"],
    # --- general ---
    "que": ["what", "cual", "which", "como", "how", "por que", "why"],
    "estado": ["status", "info", "informacion", "resumen", "summary", "overview"],
    "ayuda": ["help", "asistencia", "soporte", "support", "guide"],
    "salir": ["exit", "quit", "bye", "adios", "chao", "cerrar"],
    "ver": ["show", "display", "mostrar", "visualizar", "view"],
    "obtener": ["get", "fetch", "retrieve", "obtener", "traer"],
    "listar": ["list", "enumerar", "mostrar", "display"],
    "todos": ["all", "everyone", "everything", "completo", "full"],
    "nuevo": ["new", "create", "fresh", "agregar"],
    "mio": ["my", "mine", "personal", "propio"],
    "nivel": ["level", "tier", "grado", "rank", "rango"],
    "siguiente": ["next", "proximo", "after", "avanzar"],
    "historial": ["history", "log", "registro", "pasado", "past"],
    "configuracion": ["config", "settings", "opciones", "preferences"],
    "version": ["release", "build", "patch"],
    "activar": ["enable", "activate", "encender", "turn on"],
    "desactivar": ["disable", "deactivate", "apagar", "turn off"],
    "reiniciar": ["restart", "reboot", "reset", "reiniciar"],
    "importar": ["import", "cargar", "load", "traer"],
    "exportar": ["export", "guardar", "save", "extraer"],
    "analiza": ["analyze", "analyse", "examina", "inspect", "revisar"],
    "reporta": ["report", "informe", "resumen", "summary"],
    "valida": ["validate", "verify", "verificar", "comprobar"],
    "optimiza": ["optimize", "mejorar", "improve", "tunear"],
    "monitorea": ["monitor", "watch", "observar", "seguir", "track"],
    "depura": ["debug", "diagnostica", "troubleshoot", "fix"],
    "construye": ["build", "compile", "empacar", "package"],
    "despliega": ["deploy", "lanzar", "launch", "publicar"],
    "prueba": ["test", "verificar", "validar", "check"],
    "documenta": ["document", "anotar", "escribir", "write"],
    "comparte": ["share", "difundir", "enviar", "send"],
}


def expand(tokens: list[str]) -> set[str]:
    """Expand tokens with synonyms (bidirectional lookup)."""
    result: set[str] = set(tokens)
    for tok in tokens:
        # Forward: tok is a key
        if tok in _SYNONYMS:
            result.update(_SYNONYMS[tok])
        # Reverse: tok appears as a value in some key's list
        for key, vals in _SYNONYMS.items():
            if tok in vals:
                result.add(key)
                result.update(vals)
    return result


# ── [4] Score ─────────────────────────────────────────────────────────────────


def score_intent(expanded_tokens: set[str], patterns: list[str]) -> float:
    """Compute max Jaccard+fuzzy score across all patterns for this intent."""
    if not expanded_tokens or not patterns:
        return 0.0

    best = 0.0
    exp_sorted = " ".join(sorted(expanded_tokens))

    for pattern in patterns:
        pat_norm = normalize(pattern)
        pat_tokens = tokenize(pat_norm)
        pat_expanded = expand(pat_tokens)

        if not pat_expanded:
            continue

        # Jaccard similarity
        intersection = len(expanded_tokens & pat_expanded)
        union = len(expanded_tokens | pat_expanded)
        jaccard = intersection / union if union else 0.0

        # Fuzzy similarity (difflib SequenceMatcher)
        pat_sorted = " ".join(sorted(pat_expanded))
        fuzzy = difflib.SequenceMatcher(None, exp_sorted, pat_sorted).ratio()

        score = max(jaccard, fuzzy * 0.85)
        if score > best:
            best = score

    return best


# ── [5] Extract entities ──────────────────────────────────────────────────────


def extract_entities(query: str) -> dict:
    """Extract structured entities from the raw query string."""
    return {
        "paths": re.findall(r"(?:~|\.\.?)?/[\w/\-\. ]+|~[\w/\-\.]+", query),
        "urls": re.findall(r"https?://[\w\-\.]+(?:/[\w\-\./\?=&%#]*)?", query),
        "emails": re.findall(r"[\w\.\+]+@[\w\-\.]+\.\w+", query),
        "numbers": re.findall(r"\b\d+\b", query),
        "quoted": re.findall(r'"([^"]+)"|\'([^\']+)\'', query),
    }


# ── [6] Context ───────────────────────────────────────────────────────────────

_SESSION_CONTEXT: deque[str] = deque(maxlen=3)

_RELATED: dict[str, set[str]] = {
    "shell": {"shell", "shell_history", "list_files"},
    "memory": {"memory", "memory_reflect"},
    "wisdom": {"wisdom_capture"},
    "vault": {"vault"},
    "aeon": {"aeon"},
    "economy": {"economy"},
}


def _context_boost(intent: str, scores: dict[str, float]) -> dict[str, float]:
    """Boost intents related to recent context by +0.10."""
    if not _SESSION_CONTEXT:
        return scores
    last = _SESSION_CONTEXT[-1]
    for _group, members in _RELATED.items():
        if last in members and intent in members:
            scores[intent] = min(1.0, scores.get(intent, 0.0) + 0.10)
    return scores


def record_intent(intent: str) -> None:
    """Record a resolved intent into the session context deque."""
    _SESSION_CONTEXT.append(intent)


# ── Main API ──────────────────────────────────────────────────────────────────


def detect(
    query: str, intent_patterns: dict[str, list[str]]
) -> list[tuple[str, float]]:
    """
    Run the 6-stage NLU pipeline and return top-3 (intent, score) tuples.

    Scores range 0.0–1.0, sorted descending.
    """
    norm = normalize(query)
    tokens = tokenize(norm)
    expanded = expand(tokens)

    scores: dict[str, float] = {}
    for intent, patterns in intent_patterns.items():
        scores[intent] = score_intent(expanded, patterns)

    # Apply context boost to every intent
    for intent in list(scores.keys()):
        scores = _context_boost(intent, scores)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:3]
