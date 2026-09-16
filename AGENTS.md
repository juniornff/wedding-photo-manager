# AGENTS.md — Wedding Photo Manager

## Project status
Functional. Backend (FastAPI async) + Frontend (React/Vite) built and verified. Run everything with `docker compose up` (backend :8001→:8000 in container, frontend exposed on host :5173). `README.md` is the canonical architecture reference (Mermaid ER/use-case/sequence/state/component diagrams); `plan.md` is the original spec.

## Commands
- **Run stack:** `docker compose up` — mounts root `Fotos/`, `Miniaturas/` and `data/` into the backend container. Use `docker compose up -d --build` after changing `.env` (no need to rebuild for `.env` changes: Compose injects env vars at container start)
- **Backend local:** `uvicorn app.main:app --reload` from `backend/` — run from repo root so `config.py` finds root `.env`
- **Frontend dev:** `npm run dev` from `frontend/` — Vite proxies `/api` → `VITE_PROXY_TARGET` (default `http://localhost:8000`)
- **Frontend lint:** `npm run lint` (oxlint, config in `.oxlintrc.json` — not ESLint). No typecheck script
- **Prod deploy:** `docker compose -f docker-compose.prod.yml up -d --build` on the home server (Caddy block in `Caddyfile.md`)
- **Testing:** none yet. `backend/requirements-test.txt` is vestigial; no pytest/vitest suites, no `test` scripts

## Tech stack
- **Backend:** FastAPI + SQLAlchemy (async) + SQLite (WAL) + pydantic-settings; libs Pillow (150×150 thumbnails), Authlib (Google OAuth), qrcode (table QRs)
- **Frontend:** React 19 + Vite + Tailwind v4 + React Router; native `fetch` + React Context (no axios/Redux); SSE client
- **Storage:** local filesystem `Fotos/` + `Miniaturas/` (mirrored structure); SQLite at `data/wedding.db` (path relative to CWD; `/app/data` in container)
- **Auth:** Google OAuth (admin session cookie + guest identity recovery); anonymous guests via server-generated UUID stored in localStorage
- **Deployment:** Docker Compose (backend + frontend); Caddy + Cloudflare en producción

## Env loading (.env)
- Root `.env` is the **single** source of config values (not versioned). **No `.env.example`** exists, y **no se monta dentro de los contenedores**: cada docker-compose (`docker-compose.yml` y `docker-compose.prod.yml`) reinyecta en el contenedor **solo las variables que necesita cada servicio**, interpoladas desde el `.env` raíz vía `environment:` (`.env` → Compose → env vars del contenedor). Así ningún contenedor ve secretos que no le corresponden.
- `backend/app/config.py` reads env_file from **one** candidate: the repo root `.env` (missing files are ignored) — makes local runs outside Docker work
- Real environment variables take precedence over dotenv files (pydantic-settings); en Docker mandan las env vars inyectadas por Compose y en local el `.env` raíz. `Settings` uses `extra="ignore"` so unknown vars are tolerated
- Vars del backend declaradas en Compose: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `NOVIO_EMAIL`, `NOVIO_PASSWORD`, `NOVIA_EMAIL`, `NOVIA_PASSWORD`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY`, `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, `PYTHONUNBUFFERED`. El frontend solo recibe `VITE_PROXY_TARGET`
- `FRONTEND_URL` apunta al origen canónico del frontend: lo usa CORS, los redirects post-OAuth y el `redirect_uri` de Google. En LAN es `http://localhost:5173`; en producción `https://boda.nehemiasfeliz.com`. **Google solo admite `localhost` o dominios públicos en `redirect_uri`** (jamás IPs privadas); los orígenes LAN extra que pidan CORS (p.ej. el móvil por `http://10.0.0.4:5173`) van en `CORS_ALLOWED_ORIGINS` (CSV)
- Tras el login de Google de un invitado, el backend redirige a `FRONTEND_URL/?google_user={id}`; `AuthProvider` lee el query param, guarda en localStorage la identidad y limpia la URL (`history.replaceState`). El botón "Conectar Google" de la navbar (`/api/google?user_id=`) vincula la cuenta del invitado existente. El authorize (`GET /api/google`) usa `prompt=select_account`: Google muestra siempre el selector de cuentas (no hay single sign-out de Google; el logout de la app no cierra la sesión de Google)
- **Google exige páginas legales públicas:** el OAuth consent screen pide URL de *Política de Privacidad* y *Condiciones del Servicio* (`/privacidad` y `/terminos` en `FRONTEND_URL`) y una homepage que enlace a ambas (requisito para apps en producción con OAuth; los scopes `openid/email/profile` no requieren verificación de Google)
- For local backend runs outside Docker, run from the repo root (or export the values)
- **No frontend .env** — la API es **relativa** (`import.meta.env.VITE_API_URL || ''`, sin ARG build). `VITE_PROXY_TARGET` está **definido en el `.env` raíz** (`http://backend:8000`) y Compose lo inyecta al contenedor frontend (`${VITE_PROXY_TARGET}`); el `<proxy>` de `vite.config.js` lo usa como target. En dev local (fuera de Docker) `process.env` no ve el `.env` raíz, así que cae al default `http://localhost:8000`
- **Avatares de Google:** `index.html` fija `<meta name="referrer" content="no-referrer">`. Google devuelve **429** a las imágenes de perfil (`lh3.googleusercontent.com`) cuando el `Referer` es `http` (localhost/IP LAN); sin referer cargan en dev y en producción. No rompe la API (no usa Referer; CORS va por `Origin`)

## Backend layout & quirks
- Routers under `app/routers/`: `main`, `auth`, `fotografo_secreto`, `admin`, `sse` — all mounted in `app/main.py`
- Admin user management endpoints (all `require_admin`): `GET /api/admin/users` (list w/ `role`/`email` + goal counts + table name), `PUT /api/admin/users/{id}` (rename alias), `PATCH /api/admin/users/{id}/table` (assign/clear `table_id`), `DELETE /api/admin/users/{id}?delete_photos=false` (borrar; `false`=anonimizar fotos vía `SET user_id=NULL`, `true`=borrar fotos+archivos+SSE). After mutation they do `db.expire_all()` + fresh re-fetch because the ORM identity map otherwise returns the stale `table_rel` relationship. Borrado bloquea cuentas con `role='admin'` con 400
- Models live in a single `app/models/models.py`; schemas in `app/schemas/schemas.py`; services in `app/services/` (`photo_service`, `auth_service`, `sse_manager`)
- **No Alembic.** Schema = `Base.metadata.create_all` at startup, plus hand-written `ALTER TABLE` statements in the `main.py` lifespan (`challenges.locked`, `wedding_info.carousel_interval`). `create_all` never alters existing tables; adding a column to an existing DB must follow the same try/except `ALTER TABLE` pattern (SQLite has no `ADD COLUMN IF NOT EXISTS`)
- **`user_id` nullable para fotos anónimas.** En BD nuevas `GalleryPhoto.user_id`/`ChallengePhoto.user_id` ya son `nullable=True`. En BD existentes, la migración `_ensure_nullable_user_id()` reconstruye ambas tablas (RENAME→CREATE→INSERT→DROP) de forma idempotente (`PRAGMA table_info`), preservando `UNIQUE (challenge_id, user_id)`; todas las lecturas de fotos usan OUTER JOIN a User y serializan `user_alias=None` cuando el autor fue borrado (`=> "Anónimo"` en la UI)
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
| `/admin` | AdminPage (panel de control con tabs: Dashboard, Info Boda, Carrusel, Mesas, Retos, Galería, Usuarios, Ganador) |
| `/privacidad`, `/terminos` | PrivacyPage / TermsPage (política de privacidad y condiciones; públicas, nombres de los novios dinámicos vía `GET /api/wedding-info`; contacto `juniornff@gmail.com`) |

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
- **Roles de usuario (`User.role` admin|guest):** no hay modelo `Admin`. Al arranque `init_admin` hace upsert de los usuarios `ADMIN_EMAIL`, `NOVIO_EMAIL`, `NOVIA_EMAIL` del `.env` con `role='admin'` (email+password_hash en la tabla `users`, unique index `ix_users_email`; password solo al crear, vía `get_admin_password(email)` → `ADMIN_PASSWORD`/`NOVIO_PASSWORD`/`NOVIA_PASSWORD`). El resto de usuarios nacen `role='guest'`
- Admin auth: password (`POST /api/admin/login`, cuerpo JSON `AdminLogin`) o Google OAuth + session cookies; `is_admin_email()` acepta `ADMIN_EMAIL`, `NOVIO_EMAIL`, `NOVIA_EMAIL`. Si un Google login usa un correo que ya existe como invitado, `_resolve_admin_user` **fusiona** al invitado en la cuenta admin (mueve `gallery_photos`/`challenge_photos`, copia `table_id` si falta, borra la fila invitado). El borrado del invitado se hace con `DELETE` **SQL directo** (y no `db.delete`): el unit of work flushea los UPDATE antes que los DELETE del mismo commit, y daría `UNIQUE(users.google_id)` al fijar el `google_id` en el admin. No se crean filas placeholder `admin:{email}`; la migración del lifespan borra las que queden
- Miniaturas/ replica estructura de Fotos/
- Limpieza de archivos huérfanos cada 10s (configurable via `.env`)
- SQLite con WAL mode para concurrencia
- Sensitive config in `.env`

### Fotógrafo Secreto specifics
- `GET /api/secret-photographer/dashboard` (público, sin auth): tablero completo → mesas → retos → fotos (con autor y mensaje) + `winner_table_id/name` desde WeddingInfo
- `GET /api/secret-photographer/table/{qr_code}?user_id=X`: mesa por QR con retos; cada reto incluye `my_photo` (la foto del usuario actual, si existe) — endpoint público, sin auth
- `GET /api/secret-photographer/my-table?user_id=X` (público): devuelve `{ id, name, qr_code }` de la mesa asignada al usuario o `null`; lo usa `Navbar` para el botón "Mi Mesa" (enlaza a `/fotografo-secreto/{qr_code}`), actualizándose vía evento `table-assigned` que dispara `FotografoSecretoPage` tras asignar la mesa
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
Canonical ER diagram in `README.md`. Summary: **User** (anonymous uuid+alias or Google-authenticated; `table_id` set once; `google_name`, `google_photo`; administradores con `email`+`password_hash`+`role='admin'`), **WeddingInfo** (couple names, date, color scheme, `winner_table_id`, `carousel_interval`), **CarouselPhoto**, **GalleryPhoto**, **Table** (unique QR links), **Challenge** (10 per table, `locked` flag), **ChallengePhoto** (1/user/reto, `message` field, `UniqueConstraint(challenge_id, user_id)`).

## Conventions
- `README.md` is the canonical architecture reference with Mermaid diagrams
- `plan.md` is the original specification
- This file (AGENTS.md) is the quick-start for new agent sessions
