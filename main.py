"""
Miku OCR — a Telegram bot that reads text out of images for you.

Send, paste, or forward an image and Miku will "inspect" it and hand back
the transcribed text (English, Japanese, or Chinese) in a copy-friendly code
block. Send /translate to have Miku translate between those three languages
instead of just transcribing.

Run:
    export TELEGRAM_BOT_TOKEN="..."
    export FREELLMAPI_API_KEY="..."
    python bot.py
"""

import base64
import io
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI
from PIL import Image
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
FREELLMAPI_API_KEY = os.environ["FREELLMAPI_API_KEY"]

# Self-hosted FreeLLMAPI instance (https://github.com/tashfeenahmed/freellmapi),
# an OpenAI-compatible router over free-tier quota from multiple providers.
FREELLMAPI_BASE_URL = os.environ.get("FREELLMAPI_BASE_URL", "http://localhost:3001/v1")

# "auto" lets the router's fallback chain pick a vision-capable free-tier
# model; pin this to a specific model id if you want deterministic behaviour.
MODEL = os.environ.get("FREELLMAPI_MODEL", "auto")

# Most vision-capable free-tier models top out around this edge length;
# anything bigger just burns tokens without adding OCR accuracy.
MAX_EDGE_PX = 1568

# Keep the base64 payload comfortably under typical free-tier upload caps.
MAX_UPLOAD_MB = 20

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("miku-ocr")

# httpx logs full request URLs at INFO, and Telegram's API puts the bot
# token in the URL path — silence it to keep the token out of the logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

llm_client = OpenAI(api_key=FREELLMAPI_API_KEY, base_url=FREELLMAPI_BASE_URL)

# Languages Miku can read and translate between. Keys are the codes used in
# chat_data / the /translate command; values are the names used in prompts
# and user-facing messages.
LANGUAGES = {"en": "English", "ja": "Japanese", "zh": "Chinese"}

# Accepted spellings for the /translate command, normalised to a LANGUAGES key.
LANGUAGE_ALIASES = {
    "en": "en", "eng": "en", "english": "en",
    "ja": "ja", "jp": "ja", "jpn": "ja", "japanese": "ja",
    "zh": "zh", "cn": "zh", "chinese": "zh", "mandarin": "zh",
    "zh-cn": "zh", "zh-tw": "zh", "zh-hans": "zh", "zh-hant": "zh",
}

TRANSCRIBE_SYSTEM_PROMPT = """You are the OCR engine behind a Telegram bot called Miku OCR.
Your only job is to transcribe text visible in the supplied image, exactly and
completely, with no commentary. Supported languages are English, Japanese, and
Chinese.

Rules:
- Output ONLY the transcribed text. No preamble, no "Here's the text:", no summary.
- Preserve original line breaks, paragraph breaks, and reading order as closely as
  reasonably possible for plain text.
- Do not translate, correct spelling/grammar, or paraphrase. Transcribe verbatim,
  including typos, as long as they are actually in the image.
- If the image contains no legible text at all, output exactly:
  [NO_TEXT_FOUND]
- If the image contains legible text but it is not English, Japanese, or Chinese,
  output exactly:
  [UNSUPPORTED_LANGUAGE]
- Ignore decorative elements, logos, and watermarks unless they contain the only
  text present.
- Never wrap the output in markdown code fences or quotes yourself.
"""


def _translate_system_prompt(target_name: str) -> str:
    return f"""You are the OCR + translation engine behind a Telegram bot called Miku OCR.
Your job is to read text visible in the supplied image and translate it into
{target_name}. The image text will be in English, Japanese, or Chinese.

Rules:
- Output ONLY the {target_name} translation. No preamble, no notes, no echoing
  the original text, no commentary.
- If the text in the image is already in {target_name}, output it verbatim
  (transcribed, not paraphrased) rather than "translating" it into itself.
- Preserve original line breaks and paragraph structure as closely as
  reasonably possible for plain text.
- If the image contains no legible text at all, output exactly:
  [NO_TEXT_FOUND]
- If the image contains legible text but it is not English, Japanese, or Chinese,
  output exactly:
  [UNSUPPORTED_LANGUAGE]
- Ignore decorative elements, logos, and watermarks unless they contain the only
  text present.
- Never wrap the output in markdown code fences or quotes yourself.
"""

MIKU_INTROS = [
    "Miku's taking a look~ 🔍",
    "Scanning with full concentration... 🎧",
    "Give Miku a second to read this properly...",
    "Miku's zooming in on the details~",
    "Reading pixel by pixel, just for you~",
    "Miku's eyes are locked on the screen! 👀",
    "Let Miku decode this real quick...",
    "Booting up Miku's OCR module~ 💻",
    "Hmm, let Miku squint at this for a sec...",
    "Miku's on the case! 🕵️‍♀️",
    "Analyzing text with 39% more enthusiasm~",
    "Miku's reading glasses are on 🤓",
    "One moment, Miku's parsing the pixels...",
    "Miku's putting her whole heart into this scan~",
    "Extracting text at maximum concentration! 🎤",
    "Miku's brain.exe is processing...",
    "Give Miku a beat to read this~ 🎵",
    "Scanning in progress, please stand by...",
    "Miku's got her thinking cap on 🧢",
    "Let's see what this image is hiding~",
    "Miku's tuning her focus like a vocal track 🎶",
    "Reading time! Miku's favorite~",
    "Miku's carefully tracing every letter...",
    "Just a moment, Miku's in the zone~",
    "Miku's scanning circuits are warming up...",
    "Text detection loading... 39% cuter than usual~",
    "Miku's giving this her full attention 💚",
    "Peering closely at the image~",
    "Miku's on a reading spree! 📖",
    "Decoding characters one by one...",
    "Miku's vision mode: activated 👁️",
    "Hold tight, Miku's making sense of this~",
    "Miku's double-checking every word...",
    "Scanning like it's a live performance! 🎤",
    "Miku's got this, just a sec~",
    "Bringing the text into focus...",
    "Miku's translating pixels into words~",
    "Reading with full determination! 💪",
    "Miku's almost done taking it all in~",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prep_image(raw: bytes) -> tuple[bytes, str]:
    """Downscale large images and normalise to JPEG for a cheap, fast call."""
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")

    w, h = img.size
    longest = max(w, h)
    if longest > MAX_EDGE_PX:
        scale = MAX_EDGE_PX / longest
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue(), "image/jpeg"


def _run_ocr(image_bytes: bytes, media_type: str, system_prompt: str, instruction: str) -> str:
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:{media_type};base64,{b64}"

    response = llm_client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": instruction,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri},
                    },
                ],
            },
        ],
    )

    return (response.choices[0].message.content or "").strip()


def _import_random():
    import random

    return random


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


LOGO_PATH = Path(__file__).parent / "assets" / "miku ocr logo v1.png"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caption = (
        "Hi, I'm Miku OCR! 🎤📸\n\n"
        "Send me a photo, paste an image, or forward one from another chat, and "
        "I'll read the text out of it for you — copy-paste ready. I can read "
        "English, Japanese, and Chinese.\n\n"
        "By default I just transcribe what's in the image. Send /translate en, "
        "/translate ja, or /translate zh to have me translate into that language "
        "instead — /translate off switches back to transcribe-only.\n\n"
        "Table extraction and editable docs are coming soon!"
    )
    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as logo:
            await update.message.reply_photo(photo=logo, caption=caption)
    else:
        await update.message.reply_text(caption)


async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_data = context.chat_data
    args = context.args

    if not args:
        current = chat_data.get("translate_target")
        if current:
            await update.message.reply_text(
                f"Translation mode is ON — Miku is translating into {LANGUAGES[current]}.\n"
                "Use /translate off to go back to transcribe-only, or /translate "
                "<en|ja|zh> to change the target language."
            )
        else:
            await update.message.reply_text(
                "Translation mode is OFF — Miku just transcribes text as-is.\n"
                "Use /translate <en|ja|zh> to have Miku translate into that "
                "language instead, e.g. /translate ja"
            )
        return

    arg = args[0].strip().lower()
    if arg in ("off", "none", "disable", "stop"):
        chat_data.pop("translate_target", None)
        await update.message.reply_text("Translation mode is OFF. Miku will transcribe text as-is again. 📝")
        return

    code = LANGUAGE_ALIASES.get(arg)
    if not code:
        await update.message.reply_text(
            "Miku doesn't recognise that language. Try /translate en, "
            "/translate ja, /translate zh, or /translate off."
        )
        return

    chat_data["translate_target"] = code
    await update.message.reply_text(
        f"Translation mode is ON — Miku will translate images into {LANGUAGES[code]} from now on. 🌐"
    )


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    chat_id = message.chat_id

    # Figure out what kind of image payload we got.
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id  # largest resolution
    elif message.document and (message.document.mime_type or "").startswith("image/"):
        size_mb = (message.document.file_size or 0) / (1024 * 1024)
        if size_mb > MAX_UPLOAD_MB:
            await message.reply_text(
                f"That file's a bit big for Miku ({size_mb:.1f}MB). "
                f"Try sending it under {MAX_UPLOAD_MB}MB."
            )
            return
        file_id = message.document.file_id

    if not file_id:
        return

    translate_target = context.chat_data.get("translate_target")
    if translate_target:
        target_name = LANGUAGES[translate_target]
        system_prompt = _translate_system_prompt(target_name)
        instruction = f"Translate the text in this image into {target_name}."
    else:
        system_prompt = TRANSCRIBE_SYSTEM_PROMPT
        instruction = "Transcribe the text in this image."

    random = _import_random()
    await message.reply_text(random.choice(MIKU_INTROS))
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        tg_file = await context.bot.get_file(file_id)
        raw = bytes(await tg_file.download_as_bytearray())
        image_bytes, media_type = _prep_image(raw)
        text = _run_ocr(image_bytes, media_type, system_prompt, instruction)
    except Exception:
        logger.exception("OCR failed for chat %s", chat_id)
        await message.reply_text(
            "Ah, Miku dropped the page! Something went wrong reading that image — "
            "mind trying again?"
        )
        return

    if text == "[NO_TEXT_FOUND]":
        await message.reply_text(
            "Miku looked closely but couldn't find any readable text in that image. 🎧"
        )
        return

    if text == "[UNSUPPORTED_LANGUAGE]":
        await message.reply_text(
            "Miku can see text in there, but it's not English, Japanese, or "
            "Chinese — and those are the only languages Miku reads for now. 🌐"
        )
        return

    if not text:
        await message.reply_text(
            "Hmm, Miku couldn't make anything out of that one. Maybe try a clearer photo?"
        )
        return

    # Telegram messages cap at 4096 chars — split long transcripts into
    # multiple copy-friendly code blocks.
    chunks = _chunk_text(text, 3800)
    for i, chunk in enumerate(chunks):
        prefix = "" if len(chunks) == 1 else f"Part {i + 1}/{len(chunks)}\n"
        await message.reply_text(
            f"{prefix}```\n{_escape_code_block(chunk)}\n```",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


def _chunk_text(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:size])
        text = text[size:]
    return chunks


def _escape_code_block(text: str) -> str:
    # Inside a MarkdownV2 pre/code block only backtick and backslash need escaping.
    return text.replace("\\", "\\\\").replace("`", "\\`")


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send Miku a photo or a forwarded image and I'll transcribe the text for you! 📸"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("translate", translate_cmd))
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)
    )
    app.add_handler(
        MessageHandler(
            ~filters.COMMAND & ~filters.PHOTO & ~filters.Document.IMAGE,
            handle_other,
        )
    )

    logger.info("Miku OCR is online using model %s via %s", MODEL, FREELLMAPI_BASE_URL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
