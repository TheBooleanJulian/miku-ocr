<div align="center">

# Miku OCR

**A Telegram bot that reads text out of images and hands it back as clean, copy-paste-ready English.**

![Version](https://img.shields.io/badge/version-0.4.0-00D4C8)
![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/-Telegram-26A5E4?logo=telegram&logoColor=white)
![Claude](https://img.shields.io/badge/-Claude%20API-D4A017)
![License](https://img.shields.io/badge/license-AGPLv3%20%2F%20Commercial-00D4C8.svg)

</div>

---

![Hero screenshot](assets/miku ocr logo v1.png)

## What it does

Miku OCR is a Telegram bot that transcribes English text from any image you send it. Forward a screenshot, paste a photo from clipboard, or drop an uncompressed file — Miku calls Claude Haiku 4.5 to do the heavy lifting and returns the result in a monospace block you can tap-and-hold to copy in one go. Images are automatically downscaled before the API call to keep token costs low without hurting accuracy.

## Features

- Accepts photos sent directly, pasted from clipboard, or forwarded from other chats
- Also accepts images sent as Telegram "Document" (uncompressed) files
- Returns transcribed text in a monospace block for easy one-tap copying
- Downscales images to a max edge of 1568px and re-encodes as JPEG before upload — the primary cost-control lever
- Splits very long transcripts across multiple messages so nothing is truncated
- Runs on Claude Haiku 4.5 — fast and cheap enough to run at volume

## Tech Stack

| Layer | Choice |
|---|---|
| Bot | python-telegram-bot 21.6 (polling) |
| AI | Claude API — `claude-haiku-4-5-20251001` |
| Image processing | Pillow |

## Quick Start

```bash
git clone <repo>
cd miku-ocr
pip install -r requirements.txt
cp .env.example .env
# fill in both values in .env
python main.py
```

The bot polls Telegram for updates — no public URL or webhook needed.

## Configuration

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token from [@BotFather](https://t.me/BotFather) |
| `ANTHROPIC_API_KEY` | ✅ | API key from the [Claude Console](https://console.anthropic.com/) |

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
- [x] Claude Haiku OCR with monospace output block
- [x] Image downscaling and JPEG re-encoding for cost control
- [x] Long transcript splitting across multiple messages

**Planned / Suggestions**

- Multi-language OCR support
- Translation of extracted text
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