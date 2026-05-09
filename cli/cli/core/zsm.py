"""
ZSM — ZANA Sovereign Machine v2.0

The soul of ZANA. Works without LLM, without network, without Docker.
This is what no other AI product has: a cognitive agent that stays with you
even when everything else is offline.

Every person in the world can have their own Aeon.
They can cook with it, manage their household economy, learn languages,
track their life — all without an internet connection.

Architecture:
    PersonalityEngine  — Aeon's voice per archetype + language
    SessionMemory      — 10-pair RAM buffer, context-aware
    IntentRouter       — 15 intent categories, multilingual
    CapabilityExecutor — Real sovereign capabilities (no stubs)
"""

from __future__ import annotations

import ast
import json
import operator as _op
import os
import re
import sqlite3
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from cli.core.i18n import t
from cli.tui.theme import console

ZANA_HOME = Path.home() / ".zana"

# ── Archetype voice mapping ───────────────────────────────────────────────────

_ARCHETYPE_GREETINGS = {
    "llama": "zsm.greeting.llama",
    "oraculo": "zsm.greeting.oraculo",
    "forja": "zsm.greeting.forja",
    "marea": "zsm.greeting.marea",
    "raiz": "zsm.greeting.raiz",
    "vacio": "zsm.greeting.vacio",
}

_ARCHETYPE_SUFFIXES_ES = {
    "llama": "🔥",
    "oraculo": "◈",
    "forja": "⚙",
    "marea": "~",
    "raiz": "🌳",
    "vacio": "∅",
}

_ARCHETYPE_SUFFIXES_EN = {
    "llama": "🔥",
    "oraculo": "◈",
    "forja": "⚙",
    "marea": "~",
    "raiz": "🌳",
    "vacio": "∅",
}


# ── Session Memory ────────────────────────────────────────────────────────────


class SessionMemory:
    """RAM-only circular buffer of the last 10 conversation pairs."""

    def __init__(self, maxlen: int = 10) -> None:
        self._buf: deque[tuple[str, str]] = deque(maxlen=maxlen)

    def push(self, user: str, aeon: str) -> None:
        self._buf.append((user, aeon))

    def last_user(self) -> str | None:
        return self._buf[-1][0] if self._buf else None

    def last_aeon(self) -> str | None:
        return self._buf[-1][1] if self._buf else None

    def resolve_reference(self, query: str) -> str | None:
        """If query is a reference pronoun ('eso', 'that', 'esto'), return last topic."""
        q = query.lower().strip()
        ref_words = {
            "eso",
            "esto",
            "that",
            "it",
            "lo anterior",
            "the previous",
            "ça",
            "cela",
            "quello",
            "das",
        }
        if q in ref_words and self._buf:
            return self._buf[-1][0]
        return None

    def context_line(self, lang: str = "es") -> str | None:
        if not self._buf:
            return None
        last_user, _ = self._buf[-1]
        return t("zsm.response.session_context", lang=lang, ctx=last_user[:60])


# ── Intent Router ─────────────────────────────────────────────────────────────

_INTENT_PATTERNS: dict[str, list[str]] = {
    "companion": [
        "hola",
        "hello",
        "olá",
        "bonjour",
        "ciao",
        "hallo",
        "cómo estás",
        "how are you",
        "como vai",
        "comment ça va",
        "come stai",
        "wie geht",
        "buenos días",
        "good morning",
        "bom dia",
        "buongiorno",
        "guten morgen",
        "buenas",
        "qué haces",
        "what are you doing",
        "hi ",
        "hey ",
    ],
    "help": [
        "ayuda",
        "help",
        "ajuda",
        "aide",
        "aiuto",
        "hilfe",
        "qué puedes",
        "what can you",
        "o que você pode",
        "que peux-tu",
        "cosa puoi",
        "was kannst du",
        "/help",
        "comandos",
        "commands",
    ],
    "math": [
        "cuánto",
        "how much",
        "quanto",
        "combien",
        "quanto fa",
        "wie viel",
        "calcula",
        "calculate",
        "calcule",
        "calculez",
        "calcola",
        "berechne",
        "% de",
        "% of",
        "% de ",
        "% von",
        "más",
        "menos",
        "multiplicar",
        "dividir",
        "plus",
        "minus",
        "times",
        "divided",
    ],
    "reminder": [
        "recuérdame",
        "remind me",
        "me lembre",
        "rappelle-moi",
        "ricordami",
        "erinnere mich",
        "avísame",
        "alert me",
        "avisa-me",
        "préviens-moi",
        "promemoria",
        "erinnerung",
    ],
    "economy": [
        "gasté",
        "spent",
        "gastei",
        "j'ai dépensé",
        "ho speso",
        "ausgegeben",
        "compré",
        "bought",
        "comprei",
        "j'ai acheté",
        "ho comprato",
        "gekauft",
        "presupuesto",
        "budget",
        "orçamento",
        "budget",
        "bilancio",
        "haushalt",
        "cuánto llevo",
        "how much have i",
        "quanto gastei",
        "gastos",
        "expenses",
        "despesas",
        "dépenses",
        "spese",
        "ausgaben",
        "ingresé",
        "earned",
        "recebi",
        "j'ai gagné",
        "ho guadagnato",
        "verdient",
    ],
    "language": [
        "traduce",
        "translate",
        "traduza",
        "traduis",
        "traduci",
        "übersetze",
        "cómo se dice",
        "how do you say",
        "como se diz",
        "comment dit-on",
        "come si dice",
        "wie sagt man",
        "enséñame",
        "teach me",
        "ensina-me",
        "apprends-moi",
        "insegnami",
        "lehr mich",
        "palabra",
        "word",
        "palavra",
        "mot",
        "parola",
        "wort",
    ],
    "memory": [
        "recuerda",
        "remember",
        "lembra",
        "souviens",
        "ricorda",
        "erinnere",
        "ayer",
        "yesterday",
        "ontem",
        "hier",
        "ieri",
        "gestern",
        "antes",
        "before",
        "antes",
        "avant",
        "prima",
        "vorher",
        "última vez",
        "last time",
        "última vez",
        "dernière fois",
        "l'ultima volta",
        "letztes mal",
        "qué recuerdas",
        "what do you remember",
    ],
    "vault": [
        "nota",
        "note",
        "nota",
        "note",
        "nota",
        "notiz",
        "busca",
        "search",
        "pesquisa",
        "cherche",
        "cerca",
        "suche",
        "archivo",
        "file",
        "ficheiro",
        "fichier",
        "file",
        "datei",
        "obsidian",
        "vault",
        "cofre",
        "tresor",
        "documento",
        "document",
        "documento",
        "document",
        "documento",
        "dokument",
    ],
    "cook": [
        "receta",
        "recipe",
        "receita",
        "recette",
        "ricetta",
        "rezept",
        "cocina",
        "cook",
        "cozinha",
        "cuisine",
        "cucina",
        "küche",
        "ingredientes",
        "ingredients",
        "ingredientes",
        "ingrédients",
        "ingredienti",
        "zutaten",
        "preparar",
        "prepare",
        "preparar",
        "préparer",
        "preparare",
        "zubereiten",
        "qué como",
        "what should i eat",
        "o que posso comer",
    ],
    "time": [
        "qué hora",
        "what time",
        "que horas",
        "quelle heure",
        "che ore",
        "wie spät",
        "qué día",
        "what day",
        "que dia",
        "quel jour",
        "che giorno",
        "welcher tag",
        "fecha",
        "date",
        "data",
        "date",
        "data",
        "datum",
        "hoy es",
        "today is",
        "hoje é",
    ],
    "tier": [
        "nivel",
        "level",
        "nível",
        "niveau",
        "livello",
        "level",
        "tier",
        "qué más",
        "what else",
        "o que mais",
        "qué puedo desbloquear",
        "what can i unlock",
        "siguiente nivel",
        "next level",
        "próximo nível",
        "capacidades",
        "capabilities",
        "capacidades",
    ],
    "aeon": [
        "aeón",
        "aeon",
        "mi aeón",
        "my aeon",
        "dna",
        "gen",
        "gen ",
        "archetype",
        "arquetipo",
        "estado del aeón",
        "aeon status",
        "sigil",
        "sigilo",
        "habitat",
        "hábitat",
    ],
    "ledger": [
        "ledger",
        "audit",
        "auditoría",
        "decisión",
        "decision",
        "decisões",
        "civic",
        "registro",
        "log",
        "sha",
        "hash",
        "firma",
    ],
    "skill": [
        "skill",
        "habilidad",
        "habilidade",
        "compétence",
        "abilità",
        "fähigkeit",
        "workflow",
        "flujo",
        "automatiza",
        "automate",
    ],
}


def _detect_intent(query: str) -> str:
    q = query.lower()

    # Math: detect operators or % patterns directly
    if re.search(r"\d[\s]*[+\-*/×÷^%][\s]*\d", q):
        return "math"
    if re.search(r"\d+%\s*(de|of|von|di|de)\s*\d+", q):
        return "math"

    for intent, keywords in _INTENT_PATTERNS.items():
        for kw in keywords:
            if kw in q:
                return intent

    return "general"


# ── Capability Executor ───────────────────────────────────────────────────────


def _ast_calc(node: ast.expr) -> float:
    """Recursive AST tree-walker — zero code execution, pure arithmetic."""
    _bin = {
        ast.Add: _op.add,
        ast.Sub: _op.sub,
        ast.Mult: _op.mul,
        ast.Div: _op.truediv,
        ast.Pow: _op.pow,
        ast.Mod: _op.mod,
        ast.FloorDiv: _op.floordiv,
    }
    if isinstance(node, ast.Expression):
        return _ast_calc(node.body)
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Tipo no permitido: {type(node.value).__name__}")
        return float(node.value)
    if isinstance(node, ast.UnaryOp):
        v = _ast_calc(node.operand)
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.UAdd):
            return v
        raise ValueError(f"Operador unario no permitido: {type(node.op).__name__}")
    if isinstance(node, ast.BinOp):
        fn = _bin.get(type(node.op))
        if fn is None:
            raise ValueError(f"Operador no permitido: {type(node.op).__name__}")
        return float(fn(_ast_calc(node.left), _ast_calc(node.right)))
    raise ValueError(f"Nodo no permitido: {type(node).__name__}")


def _calc(expr: str) -> float:
    """Evaluate a math expression safely using a pure AST tree-walker."""
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")
    expr = re.sub(
        r"(\d+(?:\.\d+)?)\s*%\s*(?:de|of|von|di|de)\s*(\d+(?:\.\d+)?)",
        lambda m: f"{m.group(2)} * {float(m.group(1)) / 100}",
        expr,
    )
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*%", lambda m: str(float(m.group(1)) / 100), expr)
    return _ast_calc(ast.parse(expr.strip(), mode="eval"))


def _extract_math_expr(query: str) -> str | None:
    """Extract numeric expression from natural language query."""
    q = query
    # Remove common prefixes
    for prefix in [
        "cuánto es",
        "how much is",
        "quanto fa",
        "combien fait",
        "quanto è",
        "wie viel ist",
        "calcula",
        "calculate",
        "calcule",
        "calcola",
        "berechne",
        "=",
        ":",
    ]:
        q = re.sub(rf"(?i){re.escape(prefix)}\s*", "", q)

    # Extract: numbers + operators + percentage patterns
    match = re.search(
        r"(\d[\d\s.,×÷+\-*/^%()]*(?:de|of|von|di)?\s*\d[\d\s.,×÷+\-*/^%()]*)",
        q,
    )
    if match:
        return match.group(1).strip()

    # Simple number expression
    match = re.search(r"[\d\s.,×÷+\-*/^%()]+", q)
    if match:
        return match.group(0).strip()

    return None


def _exec_math(query: str, lang: str) -> str:
    expr = _extract_math_expr(query)
    if not expr:
        return t("zsm.response.math_error", lang=lang)
    try:
        result = _calc(expr)
        # Format: integer if whole number, otherwise 2 decimal places
        formatted = str(int(result)) if result == int(result) else f"{result:,.4g}"
        return t("zsm.response.math_result", lang=lang, result=formatted)
    except Exception:
        return t("zsm.response.math_error", lang=lang)


def _exec_reminder(query: str, lang: str) -> str:
    """Save a reminder to ~/.zana/reminders.json."""
    reminders_file = ZANA_HOME / "reminders.json"

    # Extract the reminder text (everything after trigger word)
    text = re.sub(
        r"(?i)(recuérdame|remind me|me lembre|rappelle-moi|ricordami|erinnere mich|avísame)\s*",
        "",
        query,
        count=1,
    ).strip()
    if not text:
        text = query

    # Simple date hint detection
    now = datetime.now()
    when = None
    for word, delta in [
        ("mañana", timedelta(days=1)),
        ("tomorrow", timedelta(days=1)),
        ("amanhã", timedelta(days=1)),
        ("demain", timedelta(days=1)),
        ("domani", timedelta(days=1)),
        ("morgen", timedelta(days=1)),
        ("pasado mañana", timedelta(days=2)),
        ("day after tomorrow", timedelta(days=2)),
        ("próxima semana", timedelta(weeks=1)),
        ("next week", timedelta(weeks=1)),
    ]:
        if word in query.lower():
            when = (now + delta).strftime("%Y-%m-%d")
            break

    reminder = {
        "text": text,
        "created": now.isoformat(),
        "when": when,
        "done": False,
    }

    try:
        ZANA_HOME.mkdir(parents=True, exist_ok=True)
        existing = []
        if reminders_file.exists():
            existing = json.loads(reminders_file.read_text())
        existing.append(reminder)
        reminders_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    except Exception:
        pass

    return t("zsm.response.reminder_saved", lang=lang, text=text[:60])


def _exec_reminders_list(lang: str) -> str:
    """List pending reminders."""
    reminders_file = ZANA_HOME / "reminders.json"
    if not reminders_file.exists():
        return t("zsm.response.reminder_empty", lang=lang)
    try:
        items = json.loads(reminders_file.read_text())
        pending = [r for r in items if not r.get("done")]
        if not pending:
            return t("zsm.response.reminder_empty", lang=lang)
        lines = []
        for r in pending[-5:]:
            when = f" ({r['when']})" if r.get("when") else ""
            lines.append(f"  • {r['text']}{when}")
        return t("zsm.response.reminder_list", lang=lang, items="\n".join(lines))
    except Exception:
        return t("zsm.response.reminder_empty", lang=lang)


def _exec_economy(query: str, lang: str) -> str:
    """Log or query household economy."""
    economy_file = ZANA_HOME / "economy.json"
    q = query.lower()

    # Query mode
    is_query = any(
        w in q
        for w in [
            "cuánto llevo",
            "how much",
            "resumen",
            "summary",
            "quanto gastei",
            "résumé",
            "riepilogo",
            "zusammenfassung",
            "gastado",
            "spent this",
            "esta semana",
            "this week",
            "este mes",
            "this month",
        ]
    )

    if is_query:
        if not economy_file.exists():
            return t("zsm.response.economy_empty", lang=lang)
        try:
            records = json.loads(economy_file.read_text())
            week_ago = datetime.now() - timedelta(days=7)
            recent = [
                r for r in records if datetime.fromisoformat(r["date"]) >= week_ago
            ]
            if not recent:
                return t("zsm.response.economy_empty", lang=lang)
            total = sum(
                r.get("amount", 0) for r in recent if r.get("type") == "expense"
            )
            lines = [f"  • {r['category']}: {r['amount']}" for r in recent[-5:]]
            period = {
                "es": "esta semana",
                "en": "this week",
                "pt": "esta semana",
                "fr": "cette semaine",
                "it": "questa settimana",
                "de": "diese Woche",
            }.get(lang, "this week")
            return t(
                "zsm.response.economy_summary",
                lang=lang,
                period=period,
                items="\n".join(lines),
                total=total,
            )
        except Exception:
            return t("zsm.response.economy_empty", lang=lang)

    # Log mode: extract amount
    amount_match = re.search(r"[\d]+(?:[.,]\d+)?", query)
    amount = float(amount_match.group().replace(",", ".")) if amount_match else 0

    # Extract category from common patterns
    category = "general"
    for cat_kw in [
        ("mercado", "mercado"),
        ("supermercado", "mercado"),
        ("grocery", "grocery"),
        ("groceries", "grocery"),
        ("supermercado", "mercado"),
        ("supermarkt", "grocery"),
        ("restaurante", "restaurante"),
        ("restaurant", "restaurant"),
        ("transporte", "transporte"),
        ("transport", "transport"),
        ("salud", "salud"),
        ("health", "health"),
        ("saúde", "health"),
        ("educación", "educación"),
        ("education", "education"),
        ("ropa", "ropa"),
        ("clothes", "clothes"),
        ("kleidung", "clothes"),
        ("servicios", "servicios"),
        ("utilities", "utilities"),
    ]:
        if cat_kw[0] in q:
            category = cat_kw[1]
            break

    record = {
        "date": datetime.now().isoformat(),
        "type": "expense",
        "amount": amount,
        "category": category,
        "note": query[:80],
    }

    try:
        ZANA_HOME.mkdir(parents=True, exist_ok=True)
        records = []
        if economy_file.exists():
            records = json.loads(economy_file.read_text())
        records.append(record)
        economy_file.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    except Exception:
        pass

    return t("zsm.response.economy_logged", lang=lang, category=category, amount=amount)


_VOCAB_BASIC: dict[str, list[tuple[str, str, str]]] = {
    "en": [
        ("hello", "hola", "/həˈloʊ/"),
        ("thank you", "gracias", "/ˈθæŋk juː/"),
        ("water", "agua", "/ˈwɔːtər/"),
        ("food", "comida", "/fuːd/"),
        ("good", "bueno", "/ɡʊd/"),
        ("yes", "sí", "/jɛs/"),
        ("no", "no", "/noʊ/"),
        ("please", "por favor", "/pliːz/"),
    ],
    "es": [
        ("hola", "hello", "/ˈola/"),
        ("gracias", "thank you", "/ˈɡɾa.θjas/"),
        ("agua", "water", "/ˈa.ɣwa/"),
        ("bueno", "good", "/ˈbwe.no/"),
        ("amor", "love", "/aˈmoɾ/"),
        ("casa", "house", "/ˈka.sa/"),
    ],
    "fr": [
        ("bonjour", "good day", "/bɔ̃.ʒuʁ/"),
        ("merci", "thank you", "/mɛʁ.si/"),
        ("eau", "water", "/o/"),
        ("maison", "house", "/mɛ.zɔ̃/"),
        ("amour", "love", "/a.muʁ/"),
        ("beau", "beautiful", "/bo/"),
    ],
    "pt": [
        ("olá", "hello", "/oˈla/"),
        ("obrigado", "thank you", "/ob.ɾiˈɡa.du/"),
        ("água", "water", "/ˈa.ɡwɐ/"),
        ("casa", "house", "/ˈka.zɐ/"),
        ("amor", "love", "/aˈmoɾ/"),
        ("bom", "good", "/bõ/"),
    ],
    "it": [
        ("ciao", "hello/bye", "/ˈtʃa.o/"),
        ("grazie", "thank you", "/ˈɡɾa.tsje/"),
        ("acqua", "water", "/ˈak.kwa/"),
        ("casa", "house", "/ˈka.za/"),
        ("amore", "love", "/aˈmo.ɾe/"),
        ("bello", "beautiful", "/ˈbɛl.lo/"),
    ],
    "de": [
        ("hallo", "hello", "/haˈloː/"),
        ("danke", "thank you", "/ˈdaŋ.kə/"),
        ("wasser", "water", "/ˈvas.ɐ/"),
        ("haus", "house", "/haʊs/"),
        ("liebe", "love", "/ˈliː.bə/"),
        ("gut", "good", "/ɡuːt/"),
    ],
}


def _exec_language_lesson(query: str, lang: str) -> str:
    """Give a language flashcard."""
    # Detect target language from query
    target = lang  # default: teach the user's own configured language
    for lcode, names in [
        ("en", ["inglés", "english", "anglais", "inglese", "englisch", "en"]),
        ("es", ["español", "spanish", "espagnol", "spagnolo", "spanisch", "es"]),
        ("fr", ["francés", "french", "français", "francese", "französisch", "fr"]),
        (
            "pt",
            [
                "portugués",
                "portuguese",
                "português",
                "portoghese",
                "portugiesisch",
                "pt",
            ],
        ),
        ("it", ["italiano", "italian", "italien", "italiano", "it"]),
        ("de", ["alemán", "german", "deutsch", "allemand", "tedesco", "de"]),
    ]:
        if any(n in query.lower() for n in names):
            target = lcode
            break

    vocab = _VOCAB_BASIC.get(target, _VOCAB_BASIC["en"])

    # Cycle through vocab using a pointer in economy.json-style
    ptr_file = ZANA_HOME / f"vocab_ptr_{target}.txt"
    try:
        idx = int(ptr_file.read_text().strip()) if ptr_file.exists() else 0
    except Exception:
        idx = 0
    idx = idx % len(vocab)
    ptr_file.write_text(str((idx + 1) % len(vocab)))

    word, translation, pronunciation = vocab[idx]
    return t(
        "zsm.response.lang_lesson",
        lang=lang,
        target_lang=target,
        word=word,
        translation=translation,
        pronunciation=pronunciation,
    )


_BASIC_RECIPES: dict[str, str] = {
    "huevo|egg|ovo|œuf|uovo|ei": "Huevos revueltos: huevo + sal + mantequilla, 3 min en sartén",
    "pasta|spaghetti|noodle": "Pasta al ajo: hierve pasta, sofríe ajo en aceite, mezcla",
    "arroz|rice|riz|riso|reis": "Arroz básico: 1 taza arroz + 2 agua + sal, 18 min tapado",
    "pollo|chicken|frango|poulet|pollo|hühnchen": "Pollo al horno: 180°C, 45 min, sal + aceite",
    "verdura|vegetable|legume|légume": "Salteado: aceite caliente + verduras picadas + sal, 5 min",
}


def _exec_cook(query: str, lang: str) -> str:
    q = query.lower()
    for pattern, suggestion in _BASIC_RECIPES.items():
        if any(ing in q for ing in pattern.split("|")):
            ingredients = next(
                (ing for ing in pattern.split("|") if ing in q), pattern.split("|")[0]
            )
            return t(
                "zsm.response.cook_suggestion",
                lang=lang,
                ingredients=ingredients,
                suggestion=suggestion,
            )
    # No match: try vault
    vault_db = ZANA_HOME / "vault.db"
    if not vault_db.exists():
        return t("zsm.response.cook_no_vault", lang=lang)
    try:
        conn = sqlite3.connect(vault_db)
        cur = conn.cursor()
        cur.execute(
            "SELECT title, excerpt FROM fts_index WHERE fts_index MATCH ? LIMIT 1",
            (query,),
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return f"📖 {row[0]}\n  {row[1][:100]}..."
    except Exception:
        pass
    return t("zsm.response.cook_no_vault", lang=lang)


def _exec_time(lang: str) -> str:
    now = datetime.now()
    return t(
        "zsm.response.time",
        lang=lang,
        time=now.strftime("%H:%M"),
        date=now.strftime("%Y-%m-%d"),
    )


def _exec_memory_search(query: str, lang: str) -> str:
    db = ZANA_HOME / "episodic.db"
    if not db.exists():
        return t("zsm.response.no_memory", lang=lang)
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memories")
        count = cur.fetchone()[0]
        conn.close()
        if count == 0:
            return t("zsm.response.no_memory", lang=lang)
        return f"  {count:,} memorias episódicas. Usa: zana memory search {query[:20]}"
    except Exception:
        return t("zsm.response.no_memory", lang=lang)


def _exec_vault_search(query: str, lang: str) -> str:
    vault_db = ZANA_HOME / "vault.db"
    if not vault_db.exists():
        return t("zsm.response.no_vault", lang=lang)
    try:
        conn = sqlite3.connect(vault_db)
        cur = conn.cursor()
        terms = " ".join(w for w in query.split() if len(w) > 2)
        cur.execute(
            "SELECT title, excerpt FROM fts_index WHERE fts_index MATCH ? LIMIT 3",
            (terms,),
        )
        rows = cur.fetchall()
        conn.close()
        if rows:
            lines = [f"  • {r[0]}\n    {r[1][:70]}..." for r in rows]
            return "\n".join(lines)
        return t("zsm.response.no_vault", lang=lang)
    except Exception:
        return t("zsm.response.no_vault", lang=lang)


def _exec_tier(lang: str) -> str:
    from cli.core.tier import (
        detect_tier,
        tier_capabilities_text,
        tier_label,
        tier_next_action,
    )

    tier = detect_tier()
    return t(
        "zsm.response.tier_status",
        lang=lang,
        tier=tier_label(tier, lang),
        caps=tier_capabilities_text(tier, lang),
        next=tier_next_action(tier, lang),
    )


# ── Personality Engine ────────────────────────────────────────────────────────


class PersonalityEngine:
    def __init__(
        self, archetype: str = "forja", aeon_name: str = "ZANA", lang: str = "es"
    ):
        self.archetype = archetype.lower()
        self.name = aeon_name
        self.lang = lang

    def greeting(self) -> str:
        key = _ARCHETYPE_GREETINGS.get(self.archetype, "zsm.greeting.unknown")
        return t(key, lang=self.lang)

    def prefix(self) -> str:
        return _ARCHETYPE_SUFFIXES_ES.get(self.archetype, "◈")

    def wrap(self, content: str) -> str:
        """Add archetype personality prefix to a response."""
        p = self.prefix()
        return f"{p} {content}" if content else content


# ── ZSM Engine ────────────────────────────────────────────────────────────────


class ZSMEngine:
    """
    The ZANA Sovereign Machine.

    Can be instantiated with a UserProfile (for satellite multi-user)
    or standalone (for local CLI use).
    """

    def __init__(self, user_profile: Any = None, lang: str | None = None):
        self._memory = SessionMemory()
        self._lang = lang or self._resolve_lang()
        archetype, name = self._resolve_aeon(user_profile)
        self._personality = PersonalityEngine(archetype, name, self._lang)

    def _resolve_lang(self) -> str:
        val = os.environ.get("ZANA_LANG", "").strip().lower()
        if val in {"es", "en", "pt", "fr", "it", "de"}:
            return val
        env_file = ZANA_HOME / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ZANA_LANG="):
                    v = line.split("=", 1)[1].strip().lower()
                    if v in {"es", "en", "pt", "fr", "it", "de"}:
                        return v
        return "es"

    def _resolve_aeon(self, user_profile: Any) -> tuple[str, str]:
        if user_profile:
            return getattr(user_profile, "archetype", "forja"), getattr(
                user_profile, "aeon_name", "ZANA"
            )
        try:
            from cli.tui.aeon_dna import AeonProfile

            profile = AeonProfile.load()
            if profile:
                arch = (
                    profile.archetype.value
                    if hasattr(profile.archetype, "value")
                    else str(profile.archetype)
                )
                return arch.lower(), profile.name
        except Exception:
            pass
        return "forja", "ZANA"

    def respond_text(self, query: str) -> str:
        """Process query and return plain text response (for satellite bots)."""
        # Check for session reference
        ref = self._memory.resolve_reference(query)
        if ref:
            query = ref

        intent = _detect_intent(query)
        result = self._dispatch(intent, query)
        response = self._personality.wrap(result)
        self._memory.push(query, response)
        return response

    def respond(self, query: str) -> None:
        """Process query and print rich response to console (for CLI REPL)."""
        result = self.respond_text(query)
        console.print(
            f"\n[secondary]{self._personality.name} (Soberano)>[/secondary] {result}\n"
        )

    def _dispatch(self, intent: str, query: str) -> str:
        lang = self._lang
        if intent == "companion":
            return t("zsm.intent.companion", lang=lang)
        elif intent == "help":
            return t("zsm.intent.help", lang=lang)
        elif intent == "math":
            return _exec_math(query, lang)
        elif intent == "reminder":
            if any(
                w in query.lower()
                for w in ["lista", "list", "pendientes", "pending", "cuáles", "what"]
            ):
                return _exec_reminders_list(lang)
            return _exec_reminder(query, lang)
        elif intent == "economy":
            return _exec_economy(query, lang)
        elif intent == "language":
            return _exec_language_lesson(query, lang)
        elif intent == "memory":
            return _exec_memory_search(query, lang)
        elif intent == "vault":
            return _exec_vault_search(query, lang)
        elif intent == "cook":
            return _exec_cook(query, lang)
        elif intent == "time":
            return _exec_time(lang)
        elif intent == "tier":
            return _exec_tier(lang)
        elif intent == "aeon":
            return "Ejecuta: zana aeon status · zana aeon dna · zana aeon sigil"
        elif intent == "ledger":
            ledger = ZANA_HOME / "civic_ledger.jsonl"
            if ledger.exists():
                n = len(ledger.read_text().strip().splitlines())
                return f"{n} entradas en Civic Ledger. Ejecuta: zana sentinel ledger"
            return "Civic Ledger vacío. Activa con: zana start"
        elif intent == "skill":
            skills_path = ZANA_HOME / "skills_registry.json"
            if skills_path.exists():
                try:
                    data = json.loads(skills_path.read_text())
                    skills = data.get("skills", [])
                    if skills:
                        names = [s.get("name", "?") for s in skills[:5]]
                        return f"Skills activos: {', '.join(names)}"
                except Exception:
                    pass
            return "Sin skills registrados. Ejecuta: zana wisdom inbox"
        else:
            return t("zsm.response.unknown", lang=lang)


# ── Backward-compatible module-level API ─────────────────────────────────────

_default_engine: ZSMEngine | None = None


def _get_engine() -> ZSMEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = ZSMEngine()
    return _default_engine


def respond(query: str) -> None:
    """Module-level respond — compatible with existing chat.py usage."""
    _get_engine().respond(query)


def has_llm_provider() -> bool:
    """Return True if at least one LLM provider is configured."""
    from cli.core.tier import _has_llm_key

    return _has_llm_key()


def load_env_file() -> None:
    """Load ~/.zana/.env into os.environ if not already loaded."""
    env_file = ZANA_HOME / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = val.strip()
