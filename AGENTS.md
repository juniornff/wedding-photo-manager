# AGENTS.md — Wedding Photo Manager

## Project status
Functional. Backend (FastAPI async) + Frontend (React/Vite) built and verified. Run everything with `docker compose up` (backend :8000, frontend :5173). `README.md` is the canonical architecture reference (Mermaid ER/use-case/sequence/state/component diagrams); `plan.md` is the original spec.

## Commands
- **Run stack:** `docker compose up` — mounts root `Fotos/`, `Miniaturas/`, `data/` and the root `.env` into the backend container
- **Backend local:** `uvicorn app.main:app --reload` from `backend/` — see Env loading below
- **Frontend dev:** `npm run dev` from `frontend/` — Vite proxies `/api` → `http://localhost:8000`
- **Frontend lint:** `npm run lint` (oxlint, config in `.oxlintrc.json` — not ESLint). No typecheck script
- **Testing:** none yet. `backend/requirements-test.txt` is vestigial; no pytest/vitest suites, no `test` scripts

## Tech stack
- **Backend:** FastAPI + SQLAlchemy (async) + SQLite (WAL) + pydantic-settings; libs Pillow (150×150 thumbnails), Authlib (Google OAuth), qrcode (table QRs)
- **Frontend:** React 19 + Vite + Tailwind v4 + React Router; native `fetch` + React Context (no axios/Redux); SSE client
- **Storage:** local filesystem `Fotos/` + `Miniaturas/` (mirrored structure); SQLite at `data/wedding.db` (path relative to CWD; `/app/data` in container)
- **Auth:** Google OAuth (admin session cookie + guest identity recovery); anonymous guests via server-generated UUID stored in localStorage
- **Deployment:** Docker Compose (backend + frontend); Caddy aparte

## Env loading (.env)
- Root `.env` is the single source of secrets (not versioned). docker-compose mounts it to `/app/.env`
- `backend/app/config.py` reads env_file from two candidates (missing files are ignored):
  1. `backend/.env` (= `/app/.env` in the container)
  2. repo root `.env` — makes local runs outside Docker work
- Real environment variables take precedence over dotenv files; `Settings` uses `extra="ignore"` so unknown vars are tolerated
- For local backend runs outside Docker, run from the repo root (or export the values)

## Backend layout & quirks
- Routers under `app/routers/`: `main`, `auth`, `fotografo_secreto`, `admin`, `sse` — all mounted in `app/main.py`
- Models live in a single `app/models/models.py`; schemas in `app/schemas/schemas.py`; services in `app/services/` (`photo_service`, `auth_service`, `sse_manager`)
- **No Alembic.** Schema = `Base.metadata.create_all` at startup, plus hand-written `ALTER TABLE` statements in the `main.py` lifespan (`challenges.locked`, `wedding_info.carousel_interval`). `create_all` never alters existing tables; adding a column to an existing DB must follow the same try/except `ALTER TABLE` pattern (SQLite has no `ADD COLUMN IF NOT EXISTS`)
- Uploaded files served as static mounts: `/api/uploads` → `Fotos/`, `/api/thumbnails` → `Miniaturas/`
- Background task cleans orphan files every `ORPHAN_CLEANUP_INTERVAL` (default 10s)
- **Backend container runs as UID 1000** (`entrypoint.sh` fits `setuid(1000)`) — deliberate decision so files it writes match the host user; don't change without considering file ownership

## Architecture — 3 modules
| Module | Purpose |
|---|---|
| **Main** | Upload/view/download photos; wedding info + carousel + gallery |
| **Fotógrafo Secreto** | Per-table QR challenges; 10 retos/table, 1 photo/participant/reto, max = nro participantes mesa |
| **Admin** | Wedding panel; manage carousel, info, color scheme, tables, challenges, pick winner |

## Frontend routes
| Path | Component |
|---|---|
| `/` | MainPage (info boda, carrusel, galería, botón subida) |
| `/fotografo-secreto/:qr_code` | FotografoSecretoPage (mesa + retos) |
| `/admin` | AdminPage (panel de control) |

## Key business rules
- No login for guests — name/alias stored in localStorage + DB; anonymous UUID per device
- UUID generado por el servidor (uuid4 aleatorio), guardado en DB y localStorage
- Google OAuth for cross-device identity recovery; reemplaza alias con nombre de Google
- Google devuelve email, nombre y foto de perfil; la foto se muestra junto al nombre en las fotos subidas
- Files named with UUID to avoid collisions
- Thumbnails generated on upload (150x150px, manteniendo aspect ratio)
- Infinite scroll pagination (offset/limit)
- Photo directories: `Fotos/Carrucel/`, `Fotos/Galeria/`, `Fotos/Fotografo-Secreto/Mesa-XX/`
- Validation: MIME type real (inspección de bytes) + extension
- Max file size: 25 MB. All image formats accepted
- Rate limit: 15 uploads/minute por usuario
- Fotos servidas via FastAPI (sin autenticación para visualizar)
- Descarga individual y por lote (seleccionando fotos)
- Mensaje opcional (150 caracteres) al subir foto
- Admin auth: Google OAuth + session cookies + verificación de emails desde .env
- Admin inicial creado desde .env (email + password)
- Miniaturas/ replica estructura de Fotos/
- Limpieza de archivos huérfanos cada 10s (configurable via `.env`)
- SQLite con WAL mode para concurrencia
- Sensitive config in `.env`

### Fotógrafo Secreto specifics
- Un usuario se asigna a una mesa una sola vez (campo `table_id` en User); error si reasigna
- Reto bloqueado al alcanzar el número de participantes de la mesa; admin puede desbloquear solo para editar/eliminar
- QR generado como PNG estático en `Fotos/Fotografo-Secreto/Mesa-XX/QR.png`
- Admin elige ganador subjetivamente; vista en grilla agrupada por reto

## Database entities
Canonical ER diagram in `README.md`. Summary: **User** (anonymous uuid+alias or Google-authenticated; `table_id` set once; `google_name`, `google_photo`), **WeddingInfo** (couple names, date, color scheme, `winner_table_id`, `carousel_interval`), **CarouselPhoto**, **GalleryPhoto**, **Table** (unique QR links), **Challenge** (10 per table), **ChallengePhoto** (1/user/reto), **Admin** (credentials).

## Conventions
- `README.md` is the canonical architecture reference with Mermaid diagrams
- `plan.md` is the original specification
- This file (AGENTS.md) is the quick-start for new agent sessions