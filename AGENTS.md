# AGENTS.md — Wedding Photo Manager

## Project status
Functional. Backend (FastAPI async) + Frontend (React/Vite) built and verified. Run everything with `docker compose up` (backend :8001→:8000 in container, frontend exposed on host :8001). `README.md` is the canonical architecture reference (Mermaid ER/use-case/sequence/state/component diagrams); `plan.md` is the original spec.

## Commands
- **Run stack:** `docker compose up` — mounts root `Fotos/`, `Miniaturas/`, `data/` and the root `.env` into the backend container. Use `docker compose up -d --build` after changing `.env` (VITE_API_URL is a build-time ARG)
- **Backend local:** `uvicorn app.main:app --reload` from `backend/` — run from repo root so `config.py` finds root `.env`
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
- Root `.env` is the **single** source of secrets (not versioned). docker-compose mounts it to `/app/.env`. **No `.env.example`** exists.
- `backend/app/config.py` reads env_file from two candidates (missing files are ignored):
  1. `backend/.env` (= `/app/.env` in the container)
  2. repo root `.env` — makes local runs outside Docker work
- Real environment variables take precedence over dotenv files; `Settings` uses `extra="ignore"` so unknown vars are tolerated
- For local backend runs outside Docker, run from the repo root (or export the values)
- **No frontend .env** — `VITE_API_URL` is baked at build time via Dockerfile ARG (`docker compose up -d --build`)

## Backend layout & quirks
- Routers under `app/routers/`: `main`, `auth`, `fotografo_secreto`, `admin`, `sse` — all mounted in `app/main.py`
- Models live in a single `app/models/models.py`; schemas in `app/schemas/schemas.py`; services in `app/services/` (`photo_service`, `auth_service`, `sse_manager`)
- **No Alembic.** Schema = `Base.metadata.create_all` at startup, plus hand-written `ALTER TABLE` statements in the `main.py` lifespan (`challenges.locked`, `wedding_info.carousel_interval`). `create_all` never alters existing tables; adding a column to an existing DB must follow the same try/except `ALTER TABLE` pattern (SQLite has no `ADD COLUMN IF NOT EXISTS`)
- Uploaded files served as static mounts: `/api/uploads` → `Fotos/`, `/api/thumbnails` → `Miniaturas/`
- Background task cleans orphan files every `ORPHAN_CLEANUP_INTERVAL` (default 10s)
- **Backend container runs as UID 1000** (`entrypoint.sh` fits `setuid(1000)`) — deliberate decision so files it writes match the host user; don't change without considering file ownership

## SSE events
The backend broadcasts these named events via `sse_manager.broadcast()`:
| Event | Emitted by | Payload |
|---|---|---|
| `new_photo` | Main upload | `{ photo_id, url, thumbnail_url, ... }` |
| `gallery_photo_deleted` | Admin delete photo | `{ photo_id }` |
| `carousel_updated` | Admin add/reorder/delete carousel photo | `{}` |
| `info_updated` | Admin PUT wedding-info | Full `WeddingInfoResponse` |
| `new_challenge_photo` | FS upload | `{ photo_id, challenge_id, user_id, ... }` |
| `challenge_photo_deleted` | Admin delete challenge photo | `{ photo_id, challenge_id }` |
| `winner_selected` | Admin select/deselect winner | `{ winner_table_id, winner_table_name }` |

- `SSEProvider` (React Context) registers exactly the 7 events above; only `MainPage` consumes `lastEvent` (refresh gallery on `new_photo`/`gallery_photo_deleted`, carousel on `carousel_updated`, wedding info on `info_updated`). `AdminPage` does **not** use SSE
- `SecretDashboardPage` creates its **own EventSource** (`/api/events`, public) — does not depend on login
- `MainPage` refreshes gallery on both `new_photo` and `gallery_photo_deleted`; refreshes wedding info on `info_updated`

## Architecture — 3 modules
| Module | Purpose |
|---|---|
| **Main** | Upload/view/download photos; wedding info + carousel + gallery |
| **Fotógrafo Secreto** | Per-table QR challenges; 10 retos/table, 1 photo/participant/reto, max = nro participantes mesa |
| **Admin** | Wedding panel; manage carousel, info, color scheme, tables, challenges, challenge photos, pick/deselect winner |

## Frontend routes
| Path | Component |
|---|---|
| `/` | MainPage (info boda, carrusel, galería, botón subida) |
| `/fotografo-secreto` | SecretDashboardPage (tablero público en vivo de mesas/retos/fotos, ganador con animación) |
| `/fotografo-secreto/:qr_code` | FotografoSecretoPage (mesa + retos, foto propia por reto) |
| `/admin` | AdminPage (panel de control con tabs: Info, Carrusel, Galería, Mesas, Retos, Fotos Retos, Ganador) |

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
- Mensaje opcional (150 caracteres) al subir foto (galería y fotos de retos)
- Admin auth: Google OAuth + session cookies + verificación de emails desde .env
- Admin inicial creado desde .env (email + password)
- Miniaturas/ replica estructura de Fotos/
- Limpieza de archivos huérfanos cada 10s (configurable via `.env`)
- SQLite con WAL mode para concurrencia
- Sensitive config in `.env`

### Fotógrafo Secreto specifics
- `GET /api/secret-photographer/dashboard` (público, sin auth): tablero completo → mesas → retos → fotos (con autor y mensaje) + `winner_table_id/name` desde WeddingInfo
- `GET /api/secret-photographer/table/{qr_code}?user_id=X`: mesa por QR con retos; cada reto incluye `my_photo` (la foto del usuario actual, si existe) — endpoint público, sin auth
- Un usuario se asigna a una mesa una sola vez (campo `table_id` en User); error si reasigna
- Reto bloqueado al alcanzar el número de participantes de la mesa; admin puede desbloquear solo para editar/eliminar
- QR generado como PNG estático en `Fotos/Fotografo-Secreto/Mesa-XX/QR.png`
- Admin elige ganador subjetivamente; vista en grilla agrupada por reto; puede deseleccionar (vuelve a estado activo)
- Cada participante solo ve **su propia foto** por reto (deduplicación server-side, no de UI)
- Admin puede gestionar fotos de retos desde el tab `/Fotos Retos` (ver, borrar, mensaje del usuario visible)
- El dashboard público escucha SSE (`new_challenge_photo`, `challenge_photo_deleted`, `winner_selected`) con un EventSource propio (no depende del login); confetti **solo** al elegir ganador (no al deseleccionar)

## Context API (frontend)
Contextos divididos en 3 archivos cada uno (patrón canónico fast-refresh; lint limpio, 0 errores/0 warnings):
- `context/AuthContext.js` (`createContext`) + `context/AuthProvider.jsx` (`AuthProvider` component) + `context/useAuth.jsx` (`useAuth` hook)
- `context/SSEContext.js` (`createContext`) + `context/SSEProvider.jsx` (`SSEProvider` component) + `context/useSSE.jsx` (`useSSE` hook)

## Database entities
Canonical ER diagram in `README.md`. Summary: **User** (anonymous uuid+alias or Google-authenticated; `table_id` set once; `google_name`, `google_photo`), **WeddingInfo** (couple names, date, color scheme, `winner_table_id`, `carousel_interval`), **CarouselPhoto**, **GalleryPhoto**, **Table** (unique QR links), **Challenge** (10 per table, `locked` flag), **ChallengePhoto** (1/user/reto, `message` field, `UniqueConstraint(challenge_id, user_id)`), **Admin** (credentials).

## Conventions
- `README.md` is the canonical architecture reference with Mermaid diagrams
- `plan.md` is the original specification
- This file (AGENTS.md) is the quick-start for new agent sessions
