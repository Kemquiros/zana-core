"""
Telegram bot handlers — Herald Gateway v3.0.

Command surface:
  /start                welcome + quick guide
  /help                 command list
  /status               gateway health + ZFI + Sentinel stats
  /recall [n]           last N episodic memories
  /reason <fact>        forward-chaining (key=value)
  /swarm                fleet summary
  /aeon                 list Aeon fleet
  /wisdom [mine|approve <id>|reject <id>]  WisdomRules inbox
  /clear                reset session context hint

Message surface:
  Plain text   → /sense/text
  Voice note   → /sense/audio (OGG/MP4 → Whisper → response)
  Photo        → /sense/vision
  Document     → /sense/text (content extracted + filename context)
  Media group  → first photo processed, others acknowledged

Error taxonomy:
  GatewayDown    → warm retry hint, circuit breaker status
  GatewayTimeout → suggest short query, report LLM load
  GatewayRejected → report detail to user
  RateLimited    → throttle message with retry-after
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Final

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from telegram_bot import gateway_client as gw
from telegram_bot.gateway_client import GatewayDown, GatewayTimeout, GatewayRejected
from telegram_bot.rate_limiter import RateLimiter

logger = logging.getLogger("zana.telegram")

MAX_MSG_LEN: Final = 4096
ALLOWED_USERS = set(
    filter(None, os.getenv("ZANA_TELEGRAM_ALLOWED_USERS", "").split(","))
)

_limiter = RateLimiter(
    messages_per_minute=int(os.getenv("ZANA_TG_RATE_LIMIT", "10")),
    admin_ids=ALLOWED_USERS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session_id(update: Update) -> str:
    return f"tg-{update.effective_chat.id}"


def _allowed(update: Update) -> bool:
    if not ALLOWED_USERS:
        return True
    return str(update.effective_user.id) in ALLOWED_USERS


def _truncate(text: str, max_len: int = MAX_MSG_LEN - 200) -> str:
    return text if len(text) <= max_len else text[: max_len] + "\n…"


def _emotion_icon(emotion: str | None) -> str:
    return {
        "joy": "✨", "surprise": "⚡", "fear": "🛡️", "anger": "🔥",
        "sadness": "🌧️", "neutral": "🦊", "curiosity": "🦉", "trust": "🤝",
    }.get(emotion or "neutral", "🦊")


def _rate_check(update: Update) -> tuple[bool, str]:
    """Returns (ok, error_message). Call at the top of every message handler."""
    uid = str(update.effective_user.id)
    allowed, retry_after = _limiter.check(uid)
    if not allowed:
        secs = int(retry_after) + 1
        return False, f"⏳ Demasiado rápido. Espera {secs}s antes del próximo mensaje."
    return True, ""


def _gw_error_msg(e: Exception) -> str:
    """Human-friendly error message based on exception type."""
    if isinstance(e, GatewayDown):
        return (
            "⚠️ *Núcleo desconectado.*\n"
            "Mi base local no responde. Verifica que ZANA esté corriendo:\n"
            "`zana status`\n`zana start`"
        )
    if isinstance(e, GatewayTimeout):
        return (
            "⏱️ *Tiempo de espera excedido.*\n"
            "El modelo tardó demasiado. Intenta con una consulta más corta "
            "o verifica la carga del servidor."
        )
    if isinstance(e, GatewayRejected):
        return f"🚫 *Solicitud rechazada:* `{e}`"
    return f"⚠️ Error inesperado: `{str(e)[:150]}`"


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        await update.message.reply_text("⛔ Acceso denegado.")
        return
    text = (
        "🦊 *¡ZANA en línea! Tu Aeon ha despertado.*\n\n"
        "Soy tu Córtex Cognitivo Soberano — vivo en tu hardware, "
        "aprendo contigo y evoluciono mientras duermes.\n\n"
        "*Comandos de control:*\n"
        "`/status`  — signos vitales y ZFI\n"
        "`/recall [n]`  — últimos N recuerdos episódicos\n"
        "`/reason fact=value`  — razonamiento simbólico\n"
        "`/wisdom`  — inbox de sabiduría auto-generada\n"
        "`/swarm`  — estado del enjambre Red Queen\n"
        "`/aeon`  — flota de Aeons\n"
        "`/clear`  — limpiar contexto de sesión\n"
        "`/help`  — esta lista\n\n"
        "💡 Escríbeme, mándame voz, fotos o documentos.\n\n"
        "_JUNTOS HACEMOS TEMBLAR LOS CIELOS._"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ── /help ─────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await cmd_start(update, ctx)


# ── /clear ────────────────────────────────────────────────────────────────────

async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    ctx.chat_data.clear()
    await update.message.reply_text(
        "🧹 Contexto de sesión limpiado.\n"
        "_La siguiente conversación empieza fresca — las memorias persistentes están intactas._",
        parse_mode=ParseMode.MARKDOWN,
    )


# ── /status ───────────────────────────────────────────────────────────────────

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        data = await gw.health()
        backends = data.get("backends", {})
        lines = ["🦊 *Signos vitales del Aeon*\n"]
        icons = {
            "stt": "🎤 Oídos", "tts": "🔊 Voz", "llm": "🧠 Córtex",
            "vision": "👁️ Ojos", "kalman": "📐 Filtro Bayesiano",
            "armor": "🛡️ Escudo Rust",
        }
        for k, v in backends.items():
            lines.append(f"{icons.get(k, f'· {k}')}: `{v}`")

        # Append Sentinel stats
        try:
            s = await gw.sentinel_status()
            total = s.get("stats", {}).get("total", 0)
            ledger = s.get("ledger_entries", 0)
            lines.append(f"\n📜 Civic Ledger: `{ledger}` entradas · Eventos: `{total}`")
        except Exception:
            pass

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)


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
                "🤔 _Aún no tenemos recuerdos juntos. ¡Hablemos!_",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        lines = [f"🦉 *Últimos {len(records)} intercambios:*\n"]
        for r in records:
            ts = (r.get("created_at") or "")[:16]
            role = "Tú" if r.get("role") == "user" else "Yo"
            content = (r.get("content") or "")[:80]
            lines.append(f"`{ts}` *{role}:* {content}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)


# ── /reason ───────────────────────────────────────────────────────────────────

async def cmd_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    if not ctx.args:
        await update.message.reply_text(
            "🦊 Usa: `/reason fact_key=value`\nEjemplo: `/reason energia_baja=true`",
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
                f"🧠 Hecho `{fact_raw}` registrado.\n_Sin nuevas deducciones todavía._",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        lines = [f"⚡ *Razonando sobre:* `{fact_raw}`\n"]
        for d in deductions:
            conf = d.get("confidence", 0)
            bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
            lines.extend([
                f"*{d.get('rule', '?')}*",
                f"`{bar}` {conf:.0%}",
                f"→ _{d.get('conclusion', '?')}_",
            ])
            if d.get("action"):
                lines.append(f"⚔️ `{d['action']}`")
            lines.append("")
        if result.get("swarm_rule"):
            sr = result["swarm_rule"]
            lines.append(f"🌐 _Red Z: {sr.get('name')} ({sr.get('votes')} Aeons coinciden)_")
        await update.message.reply_text(
            _truncate("\n".join(lines)), parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)


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
            f"🔥 *Torneo Red Queen — {'Entrenando' if running else 'Descansando'}* {icon}\n",
            f"⚔️ Guerreros: `{summary.get('total', 0)}`",
            f"🧬 Activos: `{summary.get('active', 0)}`",
            f"🏆 Legendarios: `{summary.get('legends', 0)}`",
            f"📈 Aptitud media: `{summary.get('avg_fitness', 0):.3f}`",
            f"🌀 Generación: `{data.get('current_generation', 0)}`",
        ]
        if not running:
            lines.append("\n_`zana swarm init` para que comiencen a evolucionar._")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)


# ── /aeon ─────────────────────────────────────────────────────────────────────

async def cmd_aeon(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    aeons = await gw.aeon_list()
    if not aeons:
        await update.message.reply_text(
            "_No hay otros Aeons registrados._", parse_mode=ParseMode.MARKDOWN
        )
        return
    lines = ["✨ *Flota disponible:*\n"]
    tier_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}
    for a in aeons:
        icon = tier_icon.get(a.get("cost_tier", "low"), "·")
        lines.append(f"{icon} *{a['name']}* `{a['id']}`")
        lines.append(f"  _{a.get('description', '')}_ — `{a.get('model', '?')}`")
    lines.append("\n_`zana aeon use <id>` para cambiar._")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ── /wisdom ───────────────────────────────────────────────────────────────────

async def cmd_wisdom(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    args = ctx.args or []

    if args and args[0] == "mine":
        try:
            data = await gw.wisdom_mine()
            await update.message.reply_text(
                f"🔬 *Minería completada*\n"
                f"Trayectorias: `{data.get('mined', 0)}`  →  "
                f"Nuevas propuestas: `{data.get('proposed', 0)}`\n\n"
                "_Usa `/wisdom` para revisar._",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)
        return

    if len(args) >= 2 and args[0] == "approve":
        try:
            data = await gw.wisdom_approve(args[1])
            await update.message.reply_text(
                f"✅ *Skill activada:* `{data.get('name', '?')}`\n"
                f"ID: `{data.get('skill_id', '?')}`",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)
        return

    if len(args) >= 2 and args[0] == "reject":
        try:
            await gw.wisdom_reject(args[1])
            await update.message.reply_text(f"🗑️ Propuesta `{args[1]}` rechazada.", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)
        return

    # Show inbox with inline keyboard buttons
    try:
        data = await gw.wisdom_inbox()
        pending = data.get("pending", [])
        stats = data.get("stats", {})

        if not pending:
            await update.message.reply_text(
                f"🧠 *Wisdom Inbox — vacío*\n\n"
                f"✅ {stats.get('approved', 0)} aprobadas  ·  🗑️ {stats.get('rejected', 0)} rechazadas\n\n"
                "_`/wisdom mine` para extraer patrones._",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        for p in pending[:5]:
            conf = p.get("confidence", 0)
            bar = "█" * int(conf * 5) + "░" * (5 - int(conf * 5))
            text = (
                f"🧠 *{p['name']}*\n"
                f"Dominio: `{p.get('domain', '?')}` · `{bar}` {conf:.0%}\n"
                f"_{p.get('trigger', 'Sin trigger')}_\n"
            )
            if p.get("steps"):
                text += "\n".join(f"  {i+1}. {s}" for i, s in enumerate(p["steps"][:3]))

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(f"✅ Aprobar", callback_data=f"wisdom:approve:{p['id']}"),
                InlineKeyboardButton(f"🗑️ Rechazar", callback_data=f"wisdom:reject:{p['id']}"),
            ]])
            await update.message.reply_text(
                _truncate(text), parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
            )

        if len(pending) > 5:
            await update.message.reply_text(
                f"_... y {len(pending) - 5} más. Aprueba las primeras para continuar._",
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as e:
        await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)


# ── Text messages ─────────────────────────────────────────────────────────────

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    ok, msg = _rate_check(update)
    if not ok:
        await update.message.reply_text(msg)
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
        footer = ""
        if surprise > 2.0:
            footer = f"\n\n_⚡ Sorpresa Bayesiana: {surprise:.2f}_"
        elif surprise > 1.2:
            footer = f"\n\n_🧐 Dato interesante — nivel {surprise:.2f}_"
        await update.message.reply_text(
            _truncate(f"{icon} {response}{footer}"), parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("sense_text error: %s", e)
        await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)


# ── Voice notes ───────────────────────────────────────────────────────────────

async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    ok, msg = _rate_check(update)
    if not ok:
        await update.message.reply_text(msg)
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
            f"🎤 _\"{transcript}\"_\n\n{icon} {response}"
            if transcript else f"{icon} {response}"
        )
        if audio_b64:
            await ctx.bot.send_voice(
                update.effective_chat.id,
                voice=base64.b64decode(audio_b64),
                caption="🔊",
            )
        else:
            await update.message.reply_text(_truncate(reply), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error("sense_audio error: %s", e)
        await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)


# ── Photos ────────────────────────────────────────────────────────────────────

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    ok, msg = _rate_check(update)
    if not ok:
        await update.message.reply_text(msg)
        return

    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
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
            lines.append(f"👁️ _{scene}_")
        if entities:
            lines.append(f"🔍 _{', '.join(entities[:5])}_")
        if response:
            lines.append(f"\n{icon} {response}")
        await update.message.reply_text(
            _truncate("\n".join(lines)) or "🦊 Sin palabras.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("sense_vision error: %s", e)
        await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)


# ── Documents ─────────────────────────────────────────────────────────────────

async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    ok, msg = _rate_check(update)
    if not ok:
        await update.message.reply_text(msg)
        return

    doc = update.message.document
    if not doc:
        return

    filename = doc.file_name or "documento"
    mime = doc.mime_type or ""
    sid = _session_id(update)

    # Only process text-like documents; skip binaries silently
    TEXT_MIMES = {
        "text/plain", "text/markdown", "text/csv",
        "application/json", "application/xml",
        "application/x-yaml", "text/x-python",
    }
    MAX_SIZE = 1_000_000  # 1 MB — larger files not sent to LLM

    if doc.file_size and doc.file_size > MAX_SIZE:
        await update.message.reply_text(
            f"📎 *{filename}* es demasiado grande para analizar ahora "
            f"({doc.file_size // 1024} KB). Límite: 1 MB.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)

    # Download and decode
    file = await ctx.bot.get_file(doc.file_id)
    raw_bytes = bytes(await file.download_as_bytearray())

    if mime in TEXT_MIMES or filename.endswith((".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv")):
        try:
            content = raw_bytes.decode("utf-8", errors="replace")[:8000]
        except Exception:
            await update.message.reply_text("⚠️ No pude leer el documento.")
            return
    else:
        await update.message.reply_text(
            f"📎 Recibí *{filename}* (`{mime or 'tipo desconocido'}`). "
            f"Aún no proceso este formato directamente — adjunta archivos `.txt`, `.md`, `.py`, `.json` o `.csv`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    caption = update.message.caption or ""
    query = f"{caption}\n\n{content}" if caption else content

    try:
        result = await gw.sense_document(query, filename, sid)
        response = result.get("response_text") or result.get("text") or "..."
        emotion = result.get("response_emotion")
        icon = _emotion_icon(emotion)
        await update.message.reply_text(
            _truncate(f"📄 *{filename}*\n\n{icon} {response}"),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("sense_document error: %s", e)
        await update.message.reply_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)


# ── Inline callbacks (wisdom approve/reject + aeon switch) ────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("wisdom:approve:"):
        wisdom_id = data.split(":", 2)[2]
        try:
            result = await gw.wisdom_approve(wisdom_id)
            await query.edit_message_text(
                f"✅ *Skill activada:* `{result.get('name', '?')}`\n"
                f"ID: `{result.get('skill_id', '?')}`\n\n"
                "_La sabiduría fue absorbida por tu Aeon._",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await query.edit_message_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)

    elif data.startswith("wisdom:reject:"):
        wisdom_id = data.split(":", 2)[2]
        try:
            await gw.wisdom_reject(wisdom_id)
            await query.edit_message_text(
                f"🗑️ Propuesta rechazada.", parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await query.edit_message_text(_gw_error_msg(e), parse_mode=ParseMode.MARKDOWN)

    elif data.startswith("aeon:"):
        aeon_id = data.split(":", 1)[1]
        await query.edit_message_text(
            f"✨ Aeon `{aeon_id}` activo.\n_Envíame un mensaje para saludarlo._",
            parse_mode=ParseMode.MARKDOWN,
        )
