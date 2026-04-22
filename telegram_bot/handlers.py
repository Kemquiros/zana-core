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
        "joy": "😊",
        "surprise": "😲",
        "fear": "😨",
        "anger": "😠",
        "sadness": "😢",
        "neutral": "🤖",
        "curiosity": "🧐",
        "trust": "🤝",
    }.get(emotion or "neutral", "🤖")


# ── /start ────────────────────────────────────────────────────────────────────


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        await update.message.reply_text("⛔ Acceso no autorizado.")
        return

    text = (
        "🧠 *ZANA — Aeon Cognitivo*\n\n"
        "Sistema cognitivo multimodal. Percibo texto, voz e imágenes.\n\n"
        "*Comandos:*\n"
        "`/status` — salud del sistema y ZFI\n"
        "`/recall [n]` — últimos N recuerdos episódicos\n"
        "`/reason fact=value` — razonamiento simbólico\n"
        "`/swarm` — estado del enjambre Red Queen\n"
        "`/aeon` — flota de Aeons disponibles\n"
        "`/help` — esta lista\n\n"
        "O simplemente *escríbeme*, *envía una nota de voz* o *una imagen*.\n\n"
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
        lines = ["⚙️ *ZANA Gateway — Online*\n"]
        icons = {
            "stt": "🎤",
            "tts": "🔊",
            "llm": "🧠",
            "vision": "👁️",
            "kalman": "📐",
            "armor": "🛡️",
        }
        for k, v in backends.items():
            lines.append(f"{icons.get(k, '·')} `{k}`: {v}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(
            "⚠️ Gateway offline. Ejecuta `zana start` en tu servidor."
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
                "_Sin registros episódicos aún._", parse_mode=ParseMode.MARKDOWN
            )
            return
        lines = [f"📚 *Últimos {len(records)} recuerdos:*\n"]
        for r in records:
            ts = (r.get("created_at") or "")[:16]
            role = "tú" if r.get("role") == "user" else "ZANA"
            content = (r.get("content") or "")[:80]
            lines.append(f"`{ts}` *{role}:* {content}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")


# ── /reason ───────────────────────────────────────────────────────────────────


async def cmd_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    if not ctx.args:
        await update.message.reply_text(
            "Uso: `/reason fact_key=value`\nEjemplo: `/reason machine_health_avg=0.3`",
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
                f"🧠 Hecho `{fact_raw}` procesado.\n_Sin deducciones producidas._",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        lines = [f"🧠 *Razonamiento* — `{fact_raw}`\n"]
        for d in deductions:
            conf = d.get("confidence", 0)
            bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
            lines.append(f"*{d.get('rule', '?')}*")
            lines.append(f"`{bar}` {conf:.0%}")
            lines.append(f"→ _{d.get('conclusion', '?')}_")
            if d.get("action"):
                lines.append(f"⚡ `{d['action']}`")
            lines.append("")

        if result.get("swarm_rule"):
            sr = result["swarm_rule"]
            lines.append(
                f"🌐 _Swarm contribuyó: {sr.get('name')} ({sr.get('votes')} votos)_"
            )

        await update.message.reply_text(
            _truncate("\n".join(lines)), parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")


# ── /swarm ────────────────────────────────────────────────────────────────────


async def cmd_swarm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        data = await gw.swarm_status()
        summary = data.get("summary", {})
        running = data.get("running", False)
        icon = "🟢" if running else "⚫"
        lines = [
            f"🐝 *Red Queen — {'Online' if running else 'Offline'}* {icon}\n",
            f"Warriors: `{summary.get('total', 0)}`",
            f"Activos: `{summary.get('active', 0)}`",
            f"Leyendas: `{summary.get('legends', 0)}`",
            f"Fitness promedio: `{summary.get('avg_fitness', 0):.3f}`",
            f"Generación: `{data.get('current_generation', 0)}`",
        ]
        if not running:
            lines.append("\n_Usa `zana swarm init` para arrancar._")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text("⚠️ Swarm offline o Gateway no disponible.")


# ── /aeon ─────────────────────────────────────────────────────────────────────


async def cmd_aeon(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    aeons = await gw.aeon_list()
    if not aeons:
        await update.message.reply_text(
            "_No se encontró el registro de Aeons._", parse_mode=ParseMode.MARKDOWN
        )
        return

    lines = ["⚔️ *Flota de Aeons disponibles:*\n"]
    tier_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}
    for a in aeons:
        icon = tier_icon.get(a.get("cost_tier", "low"), "·")
        lines.append(f"{icon} *{a['name']}* `{a['id']}`")
        lines.append(f"  _{a.get('description', '')}_ — `{a.get('model', '?')}`")

    lines.append("\n_Usa `zana aeon use <id>` para cambiar de Aeon._")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


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
        response = result.get("response_text") or result.get("text") or "…"
        emotion = result.get("response_emotion") or result.get("emotion")
        surprise = result.get("kalman_surprise", 0)

        icon = _emotion_icon(emotion)
        # Subtle metadata footer for surprise spikes
        footer = f"\n\n_{icon} surprise: {surprise:.2f}_" if surprise > 1.5 else ""

        await update.message.reply_text(
            _truncate(response + footer),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("sense_text error: %s", e)
        await update.message.reply_text("⚠️ ZANA no disponible. Intenta más tarde.")


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
            f"🎤 _{transcript}_\n\n{icon} {response}"
            if transcript
            else f"{icon} {response}"
        )

        if audio_b64:
            audio_data = base64.b64decode(audio_b64)
            await ctx.bot.send_voice(update.effective_chat.id, voice=audio_data)
        else:
            await update.message.reply_text(
                _truncate(reply), parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error("sense_audio error: %s", e)
        await update.message.reply_text("⚠️ Error procesando el audio.")


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

        lines = []
        if scene:
            lines.append(f"👁️ _Escena: {scene}_")
        if entities:
            lines.append(f"_Entidades: {', '.join(entities[:5])}_")
        if response:
            lines.append(f"\n{response}")

        await update.message.reply_text(
            _truncate("\n".join(lines)) or "Sin descripción.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("sense_vision error: %s", e)
        await update.message.reply_text("⚠️ Error procesando la imagen.")


# ── Inline callback for future buttons ───────────────────────────────────────


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("aeon:"):
        aeon_id = data.split(":", 1)[1]
        await query.edit_message_text(
            f"✓ Aeon cambiado a `{aeon_id}`.\n_Usa /sense para continuar._",
            parse_mode=ParseMode.MARKDOWN,
        )
