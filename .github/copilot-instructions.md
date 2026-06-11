# Copilot instructions for this repository

## Build, run, test, and lint

- Full local stack: `docker compose up --build`
- Frontend dev server: `cd frontend && npm run dev`
- Frontend production build: `cd frontend && npm run build`
- Backend dev server outside Docker: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Telegram bot outside Docker: `cd bot && python bot.py`
- There is no committed automated test suite or lint script in the repository today, so there is also no single-test command to run yet.

## High-level architecture

- The repo is a four-service application: PostGIS database + FastAPI backend + Vue/Vite frontend + Telegram bot. `docker-compose.yml` runs all four locally; `docker-compose.prod.yml` adds Caddy in front of the frontend container for TLS and public routing.
- The backend is the system of record. `backend/app/main.py` mounts all API routers, creates tables on startup with `Base.metadata.create_all()`, and auto-creates the superadmin from environment variables. There is an Alembic dependency in `backend/requirements.txt`, but there is no migration config checked in; schema creation is startup-driven right now.
- The frontend is a small Vue SPA with two routes: `/` (map UI) and `/auth` (login/register). `Home.vue` composes the app out of `MapView`, `FilterBar`, `AiChat`, `UserPanel`, and `ShopPanel`, with Pinia stores handling shared auth and shop state.
- The Telegram bot is a thin client over the backend API. It does not own business logic; it calls `/shops` and `/ai/chat` on the FastAPI service and formats the responses for Telegram.
- Map security is split across frontend and backend. The browser loads the AMap JS SDK with `VITE_AMAP_JS_KEY`, but requests that need `jscode` are sent to backend route `/_AMapService/...`, where `backend/app/routers/amap_proxy.py` injects `AMAP_JSCODE`. Keep this proxy flow intact; `AMAP_JSCODE` must never move into frontend code.
- AI recommendations flow through the backend. `frontend/src/components/AiChat.vue` sends the user message to `/api/v1/ai/chat`; `backend/app/routers/ai.py` builds shop context from the database and forwards it to Ollama; `backend/app/services/ollama.py` extracts any ```highlight` block from the model response and returns `highlighted_shop_ids`, which the frontend uses to emphasize markers on the map.
- Review reactions affect more than just the review list. `backend/app/services/scoring.py` recalculates shop scores from weighted top-level reviews and recalculates user weight from review reactions, so review/reaction changes can affect both shop ranking and author weight.

## Key repository conventions

- API routes live under `/api/v1` except the AMap security proxy, which intentionally lives at `/_AMapService`. Frontend API calls assume that split: `frontend/src/api/index.js` uses `/api/v1`, while Vite and Nginx proxy both `/api` and `/_AMapService` to the backend.
- Shop list and shop detail use different payload shapes on purpose. `/shops` returns the lean `ShopListOut` used for map markers; `/shops/{id}` returns `ShopOut`, built by `_build_shop_out()` in `backend/app/routers/shops.py`, which adds photos, favorite/check-in counts, and user-specific flags. If you add shop detail fields, update the SQLAlchemy model, Pydantic schema, builder helper, and frontend consumers together.
- Authentication is localStorage-based in the frontend. `access_token` and `refresh_token` are stored in the browser, the shared axios client injects the bearer token automatically, and a single 401 retry goes through `/auth/refresh` before the client clears local auth state.
- Canonical shop color values are backend-driven string keys, not arbitrary CSS names: `sagegreen`, `olivedrab`, `seagreen`, `salmon`, and `hotpink`. Those keys are shared across markdown import, backend persistence, filter chips, map markers, AI suggestions, and shop detail badges. Keep all mappings in sync when adding or renaming a color.
- Canonical shop status values are `open`, `closed`, `preparing`, and `shutdown`. These enum values are used in backend models/schemas and mapped to Chinese UI labels in the frontend.
- Markdown shop import is name-based and intentionally conservative. `parse_markdown_table()` expects a 3-column markdown table, maps Chinese color labels to canonical internal keys, skips obvious heading/stat rows, and import updates existing shops by `Shop.name` before creating new ones.
- Geocoding is deliberately serialized. `backend/app/services/geocoding.py` sleeps between AMap requests and retries on QPS-limit responses; do not parallelize import geocoding unless you also redesign the rate-limit handling.
- Most user-facing copy is Chinese. Preserve existing Chinese labels/messages unless a task specifically requires localization changes.
