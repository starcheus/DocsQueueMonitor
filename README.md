# DocsQueueMonitor

Independent Telegram bot that monitors **public** e-queue pages of foreign DP «Dokument»
passport centers and notifies subscribers when slots may have appeared.

> **This service does not book appointments, bypass CAPTCHA/Cloudflare, or handle Diia/BankID.**

## Current MVP scope

Active cities: **Prague, Warsaw, Berlin, Kraków**.

Stack: Python 3.12, aiogram 3, SQLAlchemy 2, Alembic, Playwright (primary checker), SQLite.

## Quick start

```bash
# Python 3.12 via uv recommended
uv sync --extra dev --extra browser
uv run playwright install chromium

cp .env.example .env
# Edit .env: set TELEGRAM_BOT_TOKEN and ADMIN_TELEGRAM_IDS

uv run alembic upgrade head
uv run docsqueuemonitor --seed
uv run docsqueuemonitor --run
```

Health endpoint (localhost only): `http://127.0.0.1:8080/health`

## What works now

- `/start` → language → main menu
- Subscribe / unsubscribe cities (inline buttons)
- Status of subscriptions
- Privacy delete / anonymize
- Monitoring loop with Playwright + state machine
- Telegram notification queue with RetryAfter handling

## Tests

```bash
uv run pytest
uv run ruff check src tests
uv run mypy
```

## Disclaimer

Unofficial community project. Not affiliated with DP «Dokument». Always verify on the official site.

## License

MIT
