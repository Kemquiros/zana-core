"""
Resonance Test — 5 narrative scenarios that reveal the Aeon archetype.
Not a personality quiz. A portal.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.text import Text

from zana.tui.aeon_sigil import (
    ARCHETYPE_COLORS,
    ARCHETYPE_LABELS,
    AeonArchetype,
    AeonProfile,
)
from zana.tui.theme import console

QUESTIONS = [
    {
        "id": "q1",
        "prompt": "Entras a una biblioteca con todo el conocimiento humano.\nTienes 10 minutos. ¿Qué buscas primero?",
        "options": [
            ("El libro que nadie ha leído todavía", AeonArchetype.VACIO),
            ("El mapa que conecta todos los demás libros", AeonArchetype.ORACULO),
            ("El libro que alguien necesita y no puede encontrar", AeonArchetype.MAREA),
            ("El libro que yo perdí hace años", AeonArchetype.RAIZ),
        ],
    },
    {
        "id": "q2",
        "prompt": "Tu ciudad tiene 24 horas antes de una tormenta masiva.\n¿Qué rol tomas sin que nadie te lo pida?",
        "options": [
            ("Construyo el sistema de comunicación de emergencia", AeonArchetype.FORJA),
            ("Mapeo quién necesita ayuda y quién puede darla", AeonArchetype.MAREA),
            (
                "Estudio los patrones del clima para predecir el impacto",
                AeonArchetype.ORACULO,
            ),
            ("Enciendo el fuego y convoco a la gente", AeonArchetype.LLAMA),
        ],
    },
    {
        "id": "q3",
        "prompt": "Descubres que puedes hablar con tu yo de hace 10 años.\n¿Qué le dices?",
        "options": [
            ("'Lo que construiste importa más de lo que crees'", AeonArchetype.RAIZ),
            ("'El sistema está roto — construye el tuyo'", AeonArchetype.VACIO),
            (
                "'Las personas que encuentres son el verdadero mapa'",
                AeonArchetype.MAREA,
            ),
            ("'La visión que tienes — es real, no la sueltes'", AeonArchetype.LLAMA),
        ],
    },
    {
        "id": "q4",
        "prompt": "Tienes acceso a una IA que puede resolver UN problema\nde la humanidad perfectamente. ¿Cuál eleges?",
        "options": [
            ("La pérdida de conocimiento generacional", AeonArchetype.RAIZ),
            (
                "La desconexión entre personas que podrían colaborar",
                AeonArchetype.MAREA,
            ),
            (
                "La incapacidad de predecir consecuencias de segunda vuelta",
                AeonArchetype.ORACULO,
            ),
            (
                "La falta de sistemas que sobrevivan a sus creadores",
                AeonArchetype.FORJA,
            ),
        ],
    },
    {
        "id": "q5",
        "prompt": "Eres el último humano en Marte. Tienes suficiente comida\npara 5 años. Hay señal de radio a la Tierra. ¿Qué transmites?",
        "options": [
            ("Un mapa detallado de todo lo que descubrí aquí", AeonArchetype.ORACULO),
            ("Instrucciones para que otros puedan volver", AeonArchetype.FORJA),
            (
                "Preguntas — para que alguien en la Tierra las piense",
                AeonArchetype.VACIO,
            ),
            ("Todo lo que aprendí sobre vivir en soledad", AeonArchetype.RAIZ),
        ],
    },
]


def _score_to_archetype(scores: dict[AeonArchetype, int]) -> AeonArchetype:
    if not scores:
        return AeonArchetype.UNKNOWN
    return max(scores, key=lambda a: scores[a])


def run_resonance_test(profile: AeonProfile) -> AeonArchetype:
    """Interactive resonance test. Returns determined archetype."""
    scores: dict[AeonArchetype, int] = {
        a: 0 for a in AeonArchetype if a != AeonArchetype.UNKNOWN
    }

    _print_intro(profile)

    for i, q in enumerate(QUESTIONS):
        console.print(f"\n[dim]━━━ Pregunta {i + 1} de {len(QUESTIONS)} ━━━[/dim]")
        console.print(f"\n[white]{q['prompt']}[/white]\n")
        for j, (opt_text, _archetype) in enumerate(q["options"], 1):
            console.print(f"  [dim]{j}.[/dim] {opt_text}")

        choice = _get_choice(len(q["options"]))
        chosen_archetype = q["options"][choice - 1][1]
        scores[chosen_archetype] = scores.get(chosen_archetype, 0) + 1
        console.print("  [dim]✓[/dim]\n")

    archetype = _score_to_archetype(scores)
    _print_result(archetype, profile)
    return archetype


def _print_intro(profile: AeonProfile) -> None:
    intro = Text()
    intro.append("El Test de Resonancia calibra a tu Aeón\n", style="white")
    intro.append("con tu forma de pensar.\n\n", style="white")
    intro.append(f"Sin él, {profile.name} funciona.\n", style="dim")
    intro.append(f"Con él, {profile.name} te conoce.", style="dim")

    console.print(
        Panel(
            intro,
            title="[bold magenta] ◈ RESONANCIA ◈ [/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )
    console.print()


def _get_choice(max_n: int) -> int:
    while True:
        try:
            raw = console.input(f"  [dim]→[/dim] Elige [1-{max_n}]: ").strip()
            n = int(raw)
            if 1 <= n <= max_n:
                return n
        except (ValueError, EOFError):
            pass
        console.print(f"  [dim]Por favor elige entre 1 y {max_n}.[/dim]")


def _print_result(archetype: AeonArchetype, profile: AeonProfile) -> None:
    pc, ac = ARCHETYPE_COLORS[archetype]
    name, tagline = ARCHETYPE_LABELS[archetype]

    archetype_descriptions = {
        AeonArchetype.LLAMA: (
            "Tu Aeón será directo, orientado a la acción,\n"
            "sin rodeos. Encenderá la conversación\n"
            "antes de analizarla."
        ),
        AeonArchetype.ORACULO: (
            "Tu Aeón pensará en sistemas, no en eventos.\n"
            "Buscará los patrones invisibles antes\n"
            "de dar una respuesta."
        ),
        AeonArchetype.FORJA: (
            "Tu Aeón construirá contigo, paso a paso.\n"
            "Cada respuesta será un ladrillo,\n"
            "no una teoría."
        ),
        AeonArchetype.MAREA: (
            "Tu Aeón escuchará antes de hablar.\n"
            "Priorizará el impacto en las personas\n"
            "sobre la perfección técnica."
        ),
        AeonArchetype.RAIZ: (
            "Tu Aeón recordará todo.\n"
            "Conectará lo nuevo con lo antiguo,\n"
            "y protegerá lo que construiste."
        ),
        AeonArchetype.VACIO: (
            "Tu Aeón cuestionará lo obvio.\n"
            "Preferirá la pregunta correcta\n"
            "sobre la respuesta cómoda."
        ),
    }

    desc = archetype_descriptions.get(archetype, "")

    content = Text()
    content.append("✓ Resonancia completada.\n\n", style="bold green")
    content.append("Tu Aeón es del arquetipo ", style="white")
    content.append(f"{name}\n", style=f"bold {pc}")
    content.append(f"⟡ {tagline} ⟡\n\n", style=f"dim {ac}")
    content.append(desc, style="white")
    content.append("\n\nPuedes ajustarlo en cualquier momento con ", style="dim")
    content.append("`zana aeon tune`", style="dim cyan")

    console.print(
        Panel(
            content,
            title=f"[{ac}] ◈ {profile.name} ◈ [{ac}]",
            border_style=pc,
            padding=(1, 2),
        )
    )

    # Show mini sigil preview
    _show_sigil_preview(archetype, profile)


def _show_sigil_preview(archetype: AeonArchetype, profile: AeonProfile) -> None:
    """Brief glimpse of the new sigil to mark the moment."""
    from zana.tui.aeon_sigil import _FRAME_BUILDERS, AeonStage

    pc, ac = ARCHETYPE_COLORS[archetype]
    builder = _FRAME_BUILDERS[archetype]
    seed = hash(profile.name + profile.init_at) & 0xFFFFFFFF
    frames = builder(AeonStage.ROOKIE, seed)
    art = frames[0]

    console.print()
    for line in art:
        console.print(f"  [{pc}]{line}[/{pc}]")
    console.print()
    console.print(f"  [dim]Este es {profile.name}. Aún es Rookie.[/dim]")
    console.print("  [dim]Crece con cada conversación.[/dim]")
    console.print()
