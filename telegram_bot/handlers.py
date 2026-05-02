"""
Telegram bot handlers — all commands and message types.

Command surface:
  /start                welcome + quick guide
  /help                 command list
  /status               gateway health + ZFI
  /recall [n]           last N episodic memories
  /reason <fact>        forward-chaining (key=value)
  /swarm                fleet summary
  /aeon                 list Aeon fleet
  /clear                reset session context hint

Message surface:
  Plain text   → /sense/text
  Voice note   → /sense/audio (OGG/MP4 → Whisper → response)
  Photo        → /sense/vision
  Document     → /sense/text (extracted filename as context)
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Final

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from telegram_bot import gateway_client as gw

logger = logging.getLogger("zana.telegram")

MAX_MSG_LEN: Final = 4096  # Telegram hard limit
ALLOWED_USERS = set(
    filter(None, os.getenv("ZANA_TELEGRAM_ALLOWED_USERS", "").split(","))
)


def _session_id(update: Update) -> str:
    return f"tg-{update.effective_chat.id}"


def _allowed(update: Update) -> bool:
    if not ALLOWED_USERS:
        return True
    return str(update.effective_user.id) in ALLOWED_USERS


def _truncate(text: str, max_len: int = MAX_MSG_LEN - 200) -> str:
    return text if len(text) <= max_len else text[:max_len] + "\n…"


def _emotion_icon(emotion: str | None) -> str:
    return {
        "joy": "✨",
        "surprise": "⚡",
        "fear": "🛡️",
        "anger": "🔥",
        "sadness": "🌧️",
        "neutral": "🦊",
        "curiosity": "🦉",
        "trust": "🤝",
    }.get(emotion or "neutral", "🦊")


# ── /start ────────────────────────────────────────────────────────────────────


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        await update.message.reply_text("⛔ Acceso denegado. No reconozco tu firma digital.")
        return

    text = (
        "🦊 *¡ZANA en línea! Tu Córtex Cognitivo está despierto.*\n\n"
        "Soy tu compañero digital, nacido de la lógica y diseñado para evolucionar contigo. "
        "Estoy aquí para defender tu soberanía y potenciar tu memoria.\n\n"
        "*Tus herramientas de control:*\n"
        "`/status` — Mi estado de salud y signos vitales\n"
        "`/recall [n]` — Extraer mis últimos recuerdos episódicos contigo\n"
        "`/reason fact=value` — Ponme a pensar lógicamente\n"
        "`/swarm` — Ver el enjambre de mis ancestros entrenando\n"
        "`/aeon` — Cambiar de compañero cognitivo\n"
        "`/help` — Repasar esta lista\n\n"
        "💡 *Puedes escribirme, mandarme una nota de voz o enviarme una foto.* ¡Evolucionemos juntos!\n\n"
        "_JUNTOS HACEMOS TEMBLAR LOS CIELOS._"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ── /help ─────────────────────────────────────────────────────────────────────


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await cmd_start(update, ctx)


# ── /status ───────────────────────────────────────────────────────────────────


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        data = await gw.health()
        backends = data.get("backends", {})
        lines = ["🦊 *Mis signos vitales (Gateway) — Online y estable*\n"]
        icons = {
            "stt": "🎤 Oídos",
            "tts": "🔊 Voz",
            "llm": "🧠 Córtex",
            "vision": "👁️ Ojos",
            "kalman": "📐 Corazón Difuso",
            "armor": "🛡️ Escudo de Acero",
        }
        for k, v in backends.items():
            lines.append(f"{icons.get(k, '· ' + k)}: `{v}`")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(
            "⚠️ Oh no... He perdido conexión con mi base local. ¿Podrías encenderme usando `zana start` en tu servidor?"
        )


# ── /recall ───────────────────────────────────────────────────────────────────


async def cmd_recall(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    n = 5
    if ctx.args:
        try:
            n = max(1, min(int(ctx.args[0]), 20))
        except ValueError:
            pass

    try:
        records = await gw.memory_recall(n, _session_id(update))
        if not records:
            await update.message.reply_text(
                "🤔 _Revisé mis archivos y aún no tenemos recuerdos juntos. ¡Hablemos!_", parse_mode=ParseMode.MARKDOWN
            )
            return
        lines = [f"🦉 *Consultando mis archivos... Aquí están nuestros últimos {len(records)} intercambios:*\n"]
        for r in records:
            ts = (r.get("created_at") or "")[:16]
            role = "Tú" if r.get("role") == "user" else "Yo"
            content = (r.get("content") or "")[:80]
            lines.append(f"`{ts}` *{role}:* {content}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Me duele la cabeza intentando recordar: {e}")


# ── /reason ───────────────────────────────────────────────────────────────────


async def cmd_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    if not ctx.args:
        await update.message.reply_text(
            "🦊 Dime qué analizar. Usa: `/reason fact_key=value`\nEjemplo: `/reason energia_baja=true`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    fact_raw = " ".join(ctx.args)
    remote = "--remote" in fact_raw
    fact_raw = fact_raw.replace("--remote", "").strip()

    try:
        result = await gw.reason(fact_raw, _session_id(update), remote=remote)
        deductions = result.get("deductions", [])

        if not deductions:
            await update.message.reply_text(
                f"🧠 He ingerido el hecho `{fact_raw}`.\n_Lo anoté, pero no disparó ninguna nueva lógica evolutiva aún._",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        lines = [f"⚡ *He razonado sobre esto* — `{fact_raw}`\n"]
        for d in deductions:
            conf = d.get("confidence", 0)
            bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
            lines.append(f"*{d.get('rule', '?')}*")
            lines.append(f"`{bar}` {conf:.0%}")
            lines.append(f"→ _{d.get('conclusion', '?')}_")
            if d.get("action"):
                lines.append(f"⚔️ Ejecutando: `{d['action']}`")
            lines.append("")

        if result.get("swarm_rule"):
            sr = result["swarm_rule"]
            lines.append(
                f"🌐 _Consulté con la Red Z: {sr.get('name')} ({sr.get('votes')} entidades coinciden)_"
            )

        await update.message.reply_text(
            _truncate("\n".join(lines)), parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Hubo un fallo en mi razonamiento simbólico: {e}")


# ── /swarm ────────────────────────────────────────────────────────────────────


async def cmd_swarm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        data = await gw.swarm_status()
        summary = data.get("summary", {})
        running = data.get("running", False)
        icon = "🟢" if running else "💤"
        lines = [
            f"🔥 *Torneo de Evolución (Red Queen) — {'Entrenando' if running else 'Descansando'}* {icon}\n",
            f"⚔️ Guerreros en la arena: `{summary.get('total', 0)}`",
            f"🧬 Algoritmos Activos: `{summary.get('active', 0)}`",
            f"🏆 Entidades Legendarias: `{summary.get('legends', 0)}`",
            f"📈 Aptitud promedio: `{summary.get('avg_fitness', 0):.3f}`",
            f"🌀 Generación evolutiva: `{data.get('current_generation', 0)}`",
        ]
        if not running:
            lines.append("\n_La arena está en silencio. Usa `zana swarm init` en la terminal para que comiencen a evolucionar._")
        else:
            lines.append("\n_Mis ancestros están afilando mis instintos mientras hablamos._")
            
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text("⚠️ No puedo ver el estado de la Arena evolutiva ahora mismo.")


# ── /aeon ─────────────────────────────────────────────────────────────────────


async def cmd_aeon(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    aeons = await gw.aeon_list()
    if not aeons:
        await update.message.reply_text(
            "_Miro a mi alrededor y estoy solo. No encontré otros Aeons registrados._", parse_mode=ParseMode.MARKDOWN
        )
        return

    lines = ["✨ *Tus compañeros de flota disponibles:*\n"]
    tier_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}
    for a in aeons:
        icon = tier_icon.get(a.get("cost_tier", "low"), "·")
        lines.append(f"{icon} *{a['name']}* `{a['id']}`")
        lines.append(f"  _{a.get('description', '')}_ — Model: `{a.get('model', '?')}`")

    lines.append("\n_Dime `zana aeon use <id>` en tu terminal para que otro compañero tome el mando._")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ── /wisdom ───────────────────────────────────────────────────────────────────


async def cmd_wisdom(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Show pending Auto-WisdomRules inbox. Args: approve <id> | reject <id> | mine"""
    if not _allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    args = ctx.args or []

    # /wisdom mine — trigger trajectory mining
    if args and args[0] == "mine":
        try:
            data = await gw.wisdom_mine()
            proposed = data.get("proposed", 0)
            mined = data.get("mined", 0)
            await update.message.reply_text(
                f"🔬 *Minería completada*\n"
                f"Trayectorias analizadas: `{mined}`\n"
                f"Nuevas propuestas en inbox: `{proposed}`\n\n"
                "_Usa `/wisdom` para revisar las propuestas._",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error en minería: {e}")
        return

    # /wisdom approve <id>
    if len(args) >= 2 and args[0] == "approve":
        wisdom_id = args[1]
        try:
            data = await gw.wisdom_approve(wisdom_id)
            await update.message.reply_text(
                f"✅ *Skill activada*\n"
                f"Nombre: `{data.get('name', '?')}`\n"
                f"ID: `{data.get('skill_id', '?')}`\n\n"
                "_La sabiduría fue absorbida por tu Aeon._",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error al aprobar: {e}")
        return

    # /wisdom reject <id>
    if len(args) >= 2 and args[0] == "reject":
        wisdom_id = args[1]
        try:
            await gw.wisdom_reject(wisdom_id)
            await update.message.reply_text(f"🗑️ Propuesta `{wisdom_id}` rechazada.", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error al rechazar: {e}")
        return

    # /wisdom — show inbox
    try:
        data = await gw.wisdom_inbox()
        pending = data.get("pending", [])
        stats = data.get("stats", {})

        if not pending:
            await update.message.reply_text(
                f"🧠 *Wisdom Inbox — vacío*\n\n"
                f"Aprobadas: `{stats.get('approved', 0)}`  |  Rechazadas: `{stats.get('rejected', 0)}`\n\n"
                "_Usa `/wisdom mine` para extraer patrones de tus sesiones recientes._",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        lines = [f"🧠 *Wisdom Inbox — {len(pending)} propuesta(s) pendiente(s)*\n"]
        for p in pending[:5]:  # max 5 in Telegram
            conf = p.get("confidence", 0)
            bar = "█" * int(conf * 5) + "░" * (5 - int(conf * 5))
            lines.append(f"*{p['name']}* `[{p['id']}]`")
            lines.append(f"  Dominio: `{p.get('domain', '?')}` · Confianza: `{bar}` {conf:.0%}")
            lines.append(f"  _{p.get('trigger', 'Sin trigger definido')}_")
            lines.append(f"  ✅ `/wisdom approve {p['id']}`  🗑️ `/wisdom reject {p['id']}`\n")

        if len(pending) > 5:
            lines.append(f"_... y {len(pending) - 5} más. Aprueba las primeras para continuar._")

        await update.message.reply_text(
            _truncate("\n".join(lines)), parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error accediendo al inbox: {e}")


# ── Text messages ─────────────────────────────────────────────────────────────


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    text = update.message.text or ""
    if not text.strip():
        return

    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    sid = _session_id(update)

    try:
        result = await gw.sense_text(text, sid)
        response = result.get("response_text") or result.get("text") or "..."
        emotion = result.get("response_emotion") or result.get("emotion")
        surprise = result.get("kalman_surprise", 0)

        icon = _emotion_icon(emotion)
        
        # Friendly surprise reaction if the input was unexpected
        footer = ""
        if surprise > 2.0:
            footer = f"\n\n_⚡ ¡Wow, eso fue inesperado! (Sorpresa Bayesiana: {surprise:.2f})_"
        elif surprise > 1.2:
            footer = f"\n\n_🧐 Hm, dato interesante. (Nivel de interés: {surprise:.2f})_"

        await update.message.reply_text(
            _truncate(f"{icon} {response}{footer}"),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("sense_text error: %s", e)
        await update.message.reply_text("⚠️ Perdí la conexión con el núcleo... intenta más tarde.")


# ── Voice notes ───────────────────────────────────────────────────────────────


async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.RECORD_VOICE)

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    file = await ctx.bot.get_file(voice.file_id)
    audio_bytes = bytes(await file.download_as_bytearray())
    mime = getattr(voice, "mime_type", "audio/ogg") or "audio/ogg"
    sid = _session_id(update)

    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        result = await gw.sense_audio(audio_bytes, mime, sid)
        transcript = result.get("text", "")
        response = result.get("response_text", "")
        emotion = result.get("response_emotion")
        audio_b64 = result.get("response_audio_b64")

        icon = _emotion_icon(emotion)
        reply = (
            f"🎤 _Escuché que dijiste: \"{transcript}\"_\n\n{icon} {response}"
            if transcript
            else f"{icon} {response}"
        )

        if audio_b64:
            audio_data = base64.b64decode(audio_b64)
            await ctx.bot.send_voice(update.effective_chat.id, voice=audio_data, caption="🔊 Respondí con voz.")
        else:
            await update.message.reply_text(
                _truncate(reply), parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error("sense_audio error: %s", e)
        await update.message.reply_text("⚠️ Me costó entender ese audio. Mis oídos fallaron.")


# ── Photos ────────────────────────────────────────────────────────────────────


async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    # Highest resolution photo
    photo = update.message.photo[-1]
    file = await ctx.bot.get_file(photo.file_id)
    img_bytes = bytes(await file.download_as_bytearray())
    caption = update.message.caption or ""
    sid = _session_id(update)

    try:
        result = await gw.sense_vision(img_bytes, "image/jpeg", sid, hint=caption)
        response = result.get("response_text") or result.get("text", "")
        scene = (result.get("vision_features") or {}).get("scene_type", "")
        entities = (result.get("vision_features") or {}).get("entities", [])
        emotion = result.get("response_emotion")

        icon = _emotion_icon(emotion)
        lines = []
        if scene:
            lines.append(f"👁️ _Veo una escena tipo: {scene}_")
        if entities:
            lines.append(f"🔍 _Puedo identificar: {', '.join(entities[:5])}_")
        if response:
            lines.append(f"\n{icon} {response}")

        await update.message.reply_text(
            _truncate("\n".join(lines)) or "🦊 Sin palabras ante esta imagen.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("sense_vision error: %s", e)
        await update.message.reply_text("⚠️ Mis ojos no pudieron procesar bien esta foto.")


# ── Inline callback for future buttons ───────────────────────────────────────


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("aeon:"):
        aeon_id = data.split(":", 1)[1]
        await query.edit_message_text(
            f"✨ Hemos invocado a `{aeon_id}` para que tome el mando.\n_Envíame un mensaje para saludarlo._",
            parse_mode=ParseMode.MARKDOWN,
        )
