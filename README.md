# Professional Telegram PDF Converter Bot

Production-ready, asynchronous Telegram bot built with Aiogram 3, Pillow, ReportLab, pypdf, LibreOffice Headless, PostgreSQL, Redis, and RQ.

## Quick start
With Node.js, Docker Desktop, and a bot token in `.env`, run:

    npm run dev

This starts Docker Desktop if needed, builds the bot, and starts PostgreSQL,
Redis and the conversion workers. Press Ctrl+C to stop the stack.

## Running Automated Tests
    pytest -v
