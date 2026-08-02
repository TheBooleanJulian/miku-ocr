# Miku OCR

A Telegram bot that "reads" text out of images for you — paste, send, or forward
a photo and get back clean, copy-paste-ready English text.

Runs on **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) to keep API costs low
while staying accurate for OCR-style transcription.

## What it does today

- Accepts photos sent directly, pasted from clipboard, or forwarded from other chats
- Also accepts images sent as uncompressed files (Telegram "Document" images)
- Transcribes English text and returns it in a monospace block you can tap-and-hold
  to copy in one go
- Automatically downscales large images before sending them to the API, to keep
  token usage (and cost) down without hurting OCR accuracy
- Splits very long transcripts into multiple messages so nothing gets truncated

## Planned next

- Multi-language OCR
- Translation of the extracted text
- Table-aware extraction (structured output for tabular images)
- Export to an editable document (e.g. Word/Google Docs)

## Setup

1. **Create the bot in Telegram**
   - Message [@BotFather](https://t.me/BotFather), run `/newbot`, name it "Miku OCR"
     (or whatever handle you like), and copy the token it gives you.

2. **Get an Anthropic API key**
   - From the [Claude Console](https://console.anthropic.com/), under API Keys.

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure secrets**
   Copy `.env.example` to `.env` and fill in both values:
   ```bash
   cp .env.example .env
   ```
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-your-token-from-botfather
   ANTHROPIC_API_KEY=sk-ant-...
   ```

5. **Run it**
   ```bash
   python bot.py
   ```
   The bot polls Telegram for updates — no public URL or webhook needed for
   local/simple deployments. For always-on hosting, deploy this the same way
   you've deployed your other Telegram bots (e.g. Zeabur with a persistent
   process), just make sure both env vars are set on the platform.

## Notes on cost control

- Images are downscaled to a max edge of 1568px (Claude's useful vision
  resolution ceiling) and re-encoded as JPEG before upload — this is the
  single biggest lever on token cost for image inputs.
- `max_tokens` is capped at 4096 per request, which comfortably covers a full
  page of dense text while capping worst-case output cost.
- Everything runs on Haiku rather than Sonnet/Opus, per your requirement to
  keep this cheap to run at volume.

## File overview

- `bot.py` — the whole bot: Telegram handlers + Claude OCR call
- `requirements.txt` — pinned dependencies
- `.env.example` — template for required secrets
