<div align="center">

# Miku OCR

**A Telegram bot that reads text out of images — English, Japanese, or Chinese — and hands it back clean and copy-paste-ready, with optional translation between the three.**

![Version](https://img.shields.io/badge/version-0.5.0-00D4C8)
![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/-Telegram-26A5E4?logo=telegram&logoColor=white)
![FreeLLMAPI](https://img.shields.io/badge/-FreeLLMAPI-D4A017)
![License](https://img.shields.io/badge/license-AGPLv3%20%2F%20Commercial-00D4C8.svg)

</div>

---

![Hero screenshot](assets/miku%20ocr%20logo%20v1.png)

## What it does

Miku OCR is a Telegram bot that transcribes English, Japanese, or Chinese text from any image you send it. Forward a screenshot, paste a photo from clipboard, or drop an uncompressed file — Miku reads the text and returns it in a monospace block you can tap-and-hold to copy in one go. By default she just transcribes; send `/translate en`, `/translate ja`, or `/translate zh` to have her translate between the three languages instead, and `/translate off` to go back to transcribe-only. Images are automatically downscaled before the API call to keep costs low without hurting accuracy.

Miku runs on a self-hosted [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) instance — an OpenAI-compatible proxy that routes requests across free-tier quota from multiple LLM providers — rather than a paid API key.

## Features

- Accepts photos sent directly, pasted from clipboard, or forwarded from other chats
- Also accepts images sent as Telegram "Document" (uncompressed) files
- Reads English, Japanese, and Chinese
- Optional translation between those three languages via `/translate <en|ja|zh>` (transcribe-only by default; `/translate off` to revert)
- Returns text in a monospace block for easy one-tap copying
- Downscales images to a max edge of 1568px and re-encodes as JPEG before upload — the primary cost-control lever
- Splits very long transcripts across multiple messages so nothing is truncated
- Runs on free-tier vision models via a self-hosted FreeLLMAPI proxy

## Tech Stack

| Layer | Choice |
|---|---|
| Bot | python-telegram-bot 21.6 (polling) |
| AI | Free-tier vision models via a self-hosted [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) proxy (OpenAI-compatible) |
| Image processing | Pillow |

## Quick Start

```bash
git clone <repo>
cd miku-ocr
pip install -r requirements.txt
cp .env.example .env
# fill in the values in .env — see Configuration below
python main.py
```

The bot polls Telegram for updates — no public URL or webhook needed. You'll also need a running FreeLLMAPI instance (self-hosted; see its repo for setup) with at least one vision-capable provider key configured.

## Configuration

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token from [@BotFather](https://t.me/BotFather) |
| `FREELLMAPI_API_KEY` | ✅ | Unified key from your self-hosted FreeLLMAPI dashboard |
| `FREELLMAPI_BASE_URL` | ❌ | FreeLLMAPI's `/v1` endpoint. Defaults to `http://localhost:3001/v1` |
| `FREELLMAPI_MODEL` | ❌ | Model id to pin, or `auto` (default) to use FreeLLMAPI's fallback chain |

## Project Structure

```
miku-ocr/
|-- main.py
|-- index.html
|-- requirements.txt
|-- .env.example
|-- LICENSE
|-- COMMERCIAL-LICENSE.md
`-- assets/
```

## Status / Roadmap

**Done**

- [x] Photo, clipboard paste, and forwarded image handling
- [x] Uncompressed file (Document) image handling
- [x] OCR with monospace output block
- [x] Image downscaling and JPEG re-encoding for cost control
- [x] Long transcript splitting across multiple messages
- [x] English, Japanese, and Chinese OCR
- [x] Optional translation between English, Japanese, and Chinese via `/translate`
- [x] Migrated from the Claude API to a self-hosted FreeLLMAPI proxy over free-tier providers

**Planned / Suggestions**

- Table-aware / structured extraction for tabular images
- Export to an editable document format (Word / Google Docs)
- Automated tests for the Telegram handlers and OCR integration
- CI workflow for linting and smoke-testing on push
- Webhook mode as an alternative to polling, for lower-resource always-on hosting
- Per-user rate limiting to bound API cost from a single heavy sender
- Batch handling for multiple images sent in one message/album
- Basic usage logging/dashboard (request volume, error rate) for operating at scale

## Changelog

Versioned with [semantic versioning](https://semver.org/) — MAJOR for breaking changes, MINOR for new features, PATCH for fixes.

- **v0.5.0** — *2026-08-02* — Japanese and Chinese OCR support; optional `/translate` mode between English, Japanese, and Chinese; migrated from the Claude API to a self-hosted FreeLLMAPI proxy over free-tier providers
- **v0.4.0** — *2026-08-02* — Landing page ([index.html](index.html)); dual AGPLv3/commercial licensing; expanded roadmap
- **v0.3.1** — *2026-08-02* — Silenced the `httpx` logger so the bot token no longer leaks into request logs
- **v0.2.0** — *2026-08-02* — Renamed entry point from `bot.py` to `main.py` (Zeabur's default Python entry point); added logo asset
- **v0.1.0** — *2026-08-01* — Initial release: Telegram polling bot with Claude Haiku OCR, image downscaling, long-message splitting, and Miku-flavoured status messages

## Feedback

Found a bug or have a suggestion? [Submit it here](https://forms.gle/qRCimSyoosWyNwXdA).

## License

This project is dual licensed.

- **Community Edition** — [GNU Affero General Public License v3 (AGPLv3)](LICENSE). Free to use, modify, and self-host. If you distribute a modified version or run it as a network service, you must make the corresponding source available.
- **Commercial License** — for organisations that want to embed, modify, or distribute this software without AGPLv3's obligations. See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

---

<div align="center">
<sub>Built by <a href="https://github.com/TheBooleanJulian">@TheBooleanJulian</a></sub>
</div>