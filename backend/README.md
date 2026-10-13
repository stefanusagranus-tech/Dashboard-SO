---
title: Dashboard SO C383 API
emoji: 🚀
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Dashboard SO C383 — FastAPI Backend

Backend API untuk 4 bot: Kurumi, Hana, Yui, Rei.

## Endpoints

- `GET /` — Root
- `GET /health` — Health check
- `GET /api/bots` — List semua bot
- `POST /api/kurumi/chat` — Chat Kurumi
- `POST /api/hana/chat` — Chat Hana
- `POST /api/yui/chat` — Chat Yui
- `POST /api/rei/chat` — Chat Rei

## Docs

- Swagger UI: `/docs`
- ReDoc: `/redoc`
