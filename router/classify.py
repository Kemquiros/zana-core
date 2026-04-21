"""
XANA Router — Classification Module v2

Two-dimensional routing:
  Dimension 1 — Backend:  NotebookLM | Gemini | Claude
  Dimension 2 — Model:    Haiku | Sonnet | Opus (only when backend=Claude)

Priority order:
  Claude-force → NotebookLM → Gemini → Gemini LLM classifier (fallback)
  Claude model: Opus-force → Haiku-force → Sonnet (default)
"""

from __future__ import annotations

import re
import subprocess
from enum import Enum


GEMINI_BIN = "gemini"
GEMINI_CLASSIFIER_MODEL = ""  # empty = Gemini CLI default (gemini-2.5-pro)


# ─── Enums ────────────────────────────────────────────────────────────────────

class Route(str, Enum):
    NOTEBOOKLM = "notebooklm"  # Document retrieval — 0 Claude tokens
    GEMINI = "gemini"          # General knowledge  — 0 Claude tokens
    CLAUDE = "claude"          # Reasoning / tools  — selected model


class ClaudeModel(str, Enum):
    HAIKU = "claude-haiku-4-5-20251001"  # Fast, cheap  — simple/formatting/single-step
    SONNET = "claude-sonnet-4-6"          # Balanced     — code, medium reasoning (DEFAULT)
    OPUS = "claude-opus-4-6"             # Powerful     — architecture, critical decisions


# ─── Backend Routing Patterns ─────────────────────────────────────────────────

# Override everything: these queries MUST go to Claude (any tier)
_CLAUDE_FORCE = [
    # Heavy reasoning / architecture
    r"(diseña|implement|refactor|debug|builds?|construye|crea un?)",
    r"(escribe|write|genera|generate).*(código|code|función|function|clase|class)",
    r"(edita|edit|modifica|modify|actualiza|update).*(archivo|file|código|code|función)",
    r"(arregla|fix|soluciona|solve).*(error|bug|crash|fallo)",
    r"(analiza|analyze).*(error|stack|traceback|log)",
    r"(diseña|propone|crea|define|rediseña).*(arquitectura|architecture)",
    r"(arquitectura|architecture).*(nueva|new|alternativa|refactor|propuesta)",
    r"(commit|pull.?request|\bpr\b|git\s+(push|merge|rebase))",
    r"(despliega|deploy|kubernetes|ci/cd).*(app|service|infra|cluster|pipeline)",
    r"(docker).*(compose|build|run|push|deploy|imagen|container)",
    r"(orquesta|orchestrat|agente|agent).*(diseña|new|crea|build)",
    r"multi.?step|varios pasos|multiple steps",
    # Strategy / business / master plans (Opus-tier, but still Claude)
    r"(plan maestro|master plan|roadmap completo|full roadmap)",
    r"(estrategia|strategy).*(negocio|business|empresa|inversión|escalar|scale)",
    r"(decisión crítica|critical decision|decisión de seguridad|security decision)",
    r"(escala|scale).*(sistema|empresa|producto).*(100|1000|enterprise|global)",
    # Haiku-tier transforms (still Claude, just cheap)
    r"^(formatea|format|convierte|convert|transforma|transform)\b",
    r"^(corrige|fix).*(ortografía|spelling|typo|gramática|grammar)\b",
    r"(añade|add|agrega).*(comentario|comment|docstring|type hint|tipo)",
    r"^(renombra|rename)\b.*(variable|función|clase|archivo)",
    r"(genera|generate).*(boilerplate|template|scaffold|skeleton)",
    r"(clasifica|classify|categoriza|categorize).*(este|this|los siguientes)",
    r"^(enumera|list)\b.*(archivos|imports|dependencias|errores)",
]

# Document / personal knowledge retrieval
_NOTEBOOKLM = [
    r"(qué dice|what does|what do).*(doc|nota|vault|notebook|arquitectura|sprint|archivo|file)",
    r"(busca en|search in|consulta|look up).*(vault|notas?|notebook|mis doc|mis archivos)",
    r"(en mis notas|in my notes|my (docs?|notes?)|mi vault|mi arquitectura)",
    r"(según el doc|according to|based on my|en el doc|in the doc)",
    r"notebooklm\.google\.com/notebook",
    r"(arquitectura xana|xana architecture|xana design)",
    r"(sprint|semana \d+|week \d+|w\d{2}).*(qué|what|estado|status|tareas?|tasks?)",
    r"(project|proyecto).*(doc|spec|arquitectura|diseño|architecture|design)",
    r"(portfolio|proyecto).*(estado|status|blocker|pendiente)",
    r"(obsidian|vault|second brain).*(sobre|about|contiene|has)",
    r"(resume|summarize|sintetiza).*(nota|vault|notebook|sprint|mis\s)",
    r"(resume|summarize|sintetiza).*(documento|archivo|spec).*(xana|project|proyecto)",
]

# General knowledge, web — Gemini handles entirely
_GEMINI = [
    r"^(qué es|what is|what are|cuál es|cuáles son)\b",
    r"^(cómo funciona|how does|how do)\b",
    r"^(traduc|translat)",
    r"^(resume|summarize|summarise|sintetiza|dame un resumen)",
    r"^(explica brevemente|briefly explain|define brevemente)",
    r"(búsqueda web|web search|busca en internet|search the web)",
    r"^(lista de|list of|dame \d+|give me \d+|nombra \d+)",
    r"(estadística|statistic|dato curioso|fun fact|benchmark externo)",
    r"^(cuándo|when did|who is|quién es|quién fue)\b",
    r"(últimas? noticias|latest news|trending|novedades de)\b",
    r"(precio de|cost of|price of)\b",
    r"^(compara|compare)\b.*(frameworks?|libraries|librerías|herramientas)",
]


# ─── Claude Model Selection Patterns ─────────────────────────────────────────

# Force Opus: complex reasoning, architecture, critical systems
_OPUS_FORCE = [
    r"(arquitectura|architecture).*(sistema|system|completo|full|master|global)",
    r"(diseña|architect).*(multi.?agent|agentic|agi|sistema completo)",
    r"(estrategia|strategy).*(negocio|business|empresa|company|inversión|investment)",
    r"(plan maestro|master plan|roadmap completo|full roadmap)",
    r"(decisión crítica|critical decision|trade.?off|tradeoff).*(sistema|arquitectura)",
    r"(seguridad|security|auth|crítica|critical).*(sistema|crítica|layer|producción|production|crítico)",
    r"(optimiza|optimize).*(sistema completo|full system|pipeline|latencia|costo total)",
    r"(analiza|analyze).*(completo|complete|exhaustivo|exhaustive|profundo|deep)",
    r"(diseña|design).*(protocolo|protocol|estándar|standard|framework)",
    r"orquesta.*agentes|multi.?agent orchestrat",
    r"(code review|revisión de código).*(completo|exhaustivo|critico)",
]

# Force Haiku: fast, cheap, single-step transformations
_HAIKU_FORCE = [
    r"^(formatea|format|convierte|convert|transforma|transform)\b",
    r"^(corrige|fix).*(ortografía|spelling|typo|gramática|grammar)\b",
    r"(añade|add|agrega|append).*(comentario|comment|docstring|tipo|type hint)",
    r"^(renombra|rename)\b.*(variable|función|clase|archivo)",
    r"(genera|generate).*(boilerplate|template|scaffold|skeleton)",
    r"^(extrae|extract).*(función|función|clase).*(código existente)",
    r"^(une|merge|combina|concatena)\b",
    r"^(simplifica|simplify)\b.*(expresión|función corta|one.?liner)",
    r"(clasifica|classify|categoriza|categorize).*(este|this|los siguientes)",
    r"^(enumera|list|lista)\b.*(archivos|imports|dependencias|errores)",
    r"(snippet|fragmento|ejemplo corto|short example)\b",
]


def _match_any(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return p
    return None


# ─── Backend Classifier ───────────────────────────────────────────────────────

def classify_heuristic(query: str) -> tuple[Route, str] | None:
    """
    Fast heuristic backend classification.
    Returns (Route, reason) or None if ambiguous.
    """
    m = _match_any(_CLAUDE_FORCE, query)
    if m:
        return Route.CLAUDE, f"force:{m[:40]}"

    m = _match_any(_NOTEBOOKLM, query)
    if m:
        return Route.NOTEBOOKLM, f"doc:{m[:40]}"

    m = _match_any(_GEMINI, query)
    if m:
        return Route.GEMINI, f"general:{m[:40]}"

    return None


def classify_with_gemini(query: str) -> tuple[Route, str]:
    """
    Gemini LLM micro-classifier for ambiguous queries.
    Cost: ~50 tokens — negligible.
    """
    prompt = (
        "Classify this query into exactly ONE category. Reply with ONLY the name.\n\n"
        "NOTEBOOKLM — personal docs, vault notes, sprint status, project specs.\n"
        "GEMINI — general knowledge, web, translations, definitions, external facts.\n"
        "CLAUDE — code generation, debugging, architecture, multi-step reasoning.\n\n"
        f"Query: {query}\n\nCategory:"
    )
    try:
        cmd = [GEMINI_BIN, "-p", prompt, "-o", "text"]
        if GEMINI_CLASSIFIER_MODEL:
            cmd += ["-m", GEMINI_CLASSIFIER_MODEL]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        raw = result.stdout.strip().upper()
        if "NOTEBOOKLM" in raw:
            return Route.NOTEBOOKLM, "llm_classifier"
        if "GEMINI" in raw:
            return Route.GEMINI, "llm_classifier"
        return Route.CLAUDE, "llm_classifier"
    except Exception as exc:
        return Route.CLAUDE, f"classifier_error:{exc}"


def classify(query: str) -> tuple[Route, str]:
    """Backend classification entry point."""
    result = classify_heuristic(query)
    if result is not None:
        return result
    return classify_with_gemini(query)


# ─── Claude Model Selector ────────────────────────────────────────────────────

def select_claude_model(query: str) -> tuple[ClaudeModel, str]:
    """
    Select the appropriate Claude model tier for a query.

    Tier logic:
      Opus   — architecture, strategy, complex multi-agent, security-critical
      Haiku  — formatting, single-step transforms, boilerplate, classification
      Sonnet — everything else (default, balanced)

    Returns: (ClaudeModel, reason)
    """
    m = _match_any(_OPUS_FORCE, query)
    if m:
        return ClaudeModel.OPUS, f"opus:{m[:40]}"

    m = _match_any(_HAIKU_FORCE, query)
    if m:
        return ClaudeModel.HAIKU, f"haiku:{m[:40]}"

    return ClaudeModel.SONNET, "default"
