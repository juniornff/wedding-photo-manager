# Wedding Photo Manager

[![CI](https://github.com/juniornff/wedding-photo-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/juniornff/wedding-photo-manager/actions/workflows/ci.yml)
[![CD](https://github.com/juniornff/wedding-photo-manager/actions/workflows/cd.yml/badge.svg)](https://github.com/juniornff/wedding-photo-manager/actions/workflows/cd.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-174%20backend%20%2B%2077%20frontend-blue.svg)](#tests--cicd)

Web application to manage wedding photos: guests upload, browse and download photos **without signing up**, while the couple enjoys the interactive **Secret Photographer** game (per-table challenges with QR codes) and a full admin panel.

**English** | [Español](README.es.md)

Full technical reference — architecture diagrams, REST API, business rules and repository layout — lives in **[ARCHITECTURE.md](ARCHITECTURE.md)**.

![Main page](docs/screenshots/main.png)

## Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Use it for your wedding](#use-it-for-your-wedding)
- [Configuration (.env)](#configuration-env)
- [Tests & CI/CD](#tests--cicd)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

### Main module
- Wedding info (names, date, message) and a **carousel** of the couple's photos
- **Gallery** of photos uploaded by guests, with an optional message (150 characters)
- Uploads with **no account**: anonymous per-device identity, recoverable via **Google sign-in** (name and profile photo)
- **Every image format** supported, including iPhone HEIC/HEIF (converted to JPEG on upload), up to 25 MB
- **Bulk download**: long-press a photo to select several → single ZIP (max 100) or individual files
- **Save to Google Drive** (optional): users with a linked Google account can send selections to their Drive
- **Live** gallery via SSE (new/removed photos and updates appear instantly)

### Secret Photographer module
- Every table has a **unique QR code** (PNG downloadable from the admin panel); guests scan it and are assigned to their table automatically
- **Per-table challenges** created by the admins; one photo per participant per challenge
- Each participant only sees **their own photo** per challenge — nobody else's
- **Public live dashboard** (`/fotografo-secreto`): tables → challenges → photos with author and progress, no login required
- The admin picks the **winning table**, announced live with a confetti animation

### Admin module (`/admin`)
- Wedding info, color palette, carousel
- Table management (with QR view) and challenge management (create, edit, unlock, browse photos)
- Gallery and challenge-photo moderation
- User management (admin/guest role, table assignment, delete with or without photos)
- Select/deselect the winning table

## Screenshots

| | |
|---|---|
| ![Main page](docs/screenshots/main.png) | ![Multi-selection](docs/screenshots/gallery-selection.png) |
| Main page: hero, carousel and guest gallery | Multi-selection with the download toolbar |
| ![Secret Photographer dashboard](docs/screenshots/secret-dashboard.png) | ![Admin panel](docs/screenshots/admin.png) |
| Public Secret Photographer dashboard | Admin panel |

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy (async) + SQLite (WAL mode) |
| Backend libs | Pillow (thumbnails) + pillow-heif (HEIC→JPEG), Authlib (OAuth), qrcode (QR), pydantic-settings (config) |
| Frontend | React 19 + Vite + TailwindCSS v4 + React Router |
| Frontend HTTP | Native fetch + React Context (no Redux/axios) |
| Realtime | Server-Sent Events (SSE) |
| Storage | Local filesystem (`Fotos/`, `Miniaturas/`) + SQLite (`data/wedding.db`) |
| Auth | Google OAuth + anonymous UUID (localStorage) |
| Deployment | Docker Compose; images on GHCR built by GitHub Actions (nginx included in the frontend image) |
| Testing | pytest (backend, 174 tests) + Vitest/RTL (frontend, 77 tests) + CI/CD on GitHub Actions |

## Quick start

**Requirements:** Docker with Docker Compose.

### Option A — from source (no external accounts)

```bash
git clone https://github.com/juniornff/wedding-photo-manager.git
cd wedding-photo-manager
docker compose -f docker-compose.dev.yml up --build
```

Open **http://localhost:5173** (backend also exposed on `localhost:8001`). Best for development: Vite hot-reload included.

### Option B — pre-built images (production)

Images are published to GitHub Container Registry on every push to `master` (`ghcr.io/juniornff/wedding-photo-manager-backend|-frontend`). The packages are public, so no login is needed:

```bash
docker compose up -d          # pull only, no build
```

Open **http://localhost:8080** (nginx frontend serving the SPA with `/api` and SSE proxying).

### Example credentials and `.env`

Both compose files **work without a `.env`**: they ship example credentials in the interpolation (`admin@example.com` / `admin123`, etc.). For any real use, create a `.env` in the repo root — Docker Compose reads it automatically and **overrides** the examples:

```env
ADMIN_EMAIL=your-email@example.com
ADMIN_PASSWORD=change-this
NOVIO_EMAIL=...
NOVIO_PASSWORD=...
NOVIA_EMAIL=...
NOVIA_PASSWORD=...
SECRET_KEY=a-long-random-string
FRONTEND_URL=http://localhost:8080
```

> **Important**: change the example credentials and `SECRET_KEY` before exposing the app. Full variable list under [Configuration](#configuration-env).

- Admin panel: **http://localhost:8080/admin**
- Future deployments: `TAG=<latest|sha-…|X.Y.Z>` in the `.env` picks the image version (rollback included)
- On your LAN: open `http://<machine-IP>:8080` from any device

## Use it for your wedding

1. Start the stack and sign in to `/admin` with `ADMIN_EMAIL`/`ADMIN_PASSWORD`.
2. **Wedding info**: couple names, date, message and color palette → front page and legal pages.
3. **Carousel**: upload the couple's photos.
4. **Tables**: create the reception tables; each one generates a **unique QR code** (download and print one per table).
5. **Challenges**: create the Secret Photographer challenges (any number of challenges per table).
6. Guests visit the site **with no account**, scan their table's QR and play.
7. **Winner**: when the game ends, pick the winning table in the Winner tab → announced live with confetti on the public dashboard.
8. (Optional) **Google**: connect an account from the navbar to recover identity across devices and enable Google Drive saving (requires Google OAuth credentials, see [Configuration](#configuration-env)).

## Configuration (.env)

The root `.env` file (not versioned) is the **single source of configuration**; the compose files interpolate it into each container's environment (each service only receives the variables it needs). Outside Docker, `Settings` (`backend/app/config.py`) also reads it directly (missing file is ignored). Real environment variables take precedence over the file; `extra="ignore"` tolerates unknown keys.

| Variable | Purpose |
|---|---|
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Main admin (password or Google login) |
| `NOVIO_EMAIL` / `NOVIO_PASSWORD` | Second admin (the groom) |
| `NOVIA_EMAIL` / `NOVIA_PASSWORD` | Third admin (the bride) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth (optional) |
| `SECRET_KEY` | Session-cookie signing key |
| `FRONTEND_URL` | Canonical frontend origin (CORS, OAuth redirects, Google `redirect_uri`) |
| `CORS_ALLOWED_ORIGINS` | Extra CORS origins (CSV), e.g. a phone's LAN IP |
| `TAG` | Image version in the deploy compose (default `latest`) |

Optional, with defaults in `Settings`: `ORPHAN_CLEANUP_INTERVAL=10`, `MAX_UPLOAD_SIZE=25` (MB), `RATE_LIMIT_PER_MINUTE=15`, `DRIVE_RATE_LIMIT_PER_MINUTE=60`, `DRIVE_UPLOAD_CONCURRENCY=4`, `DATABASE_URL`, `UPLOAD_DIR=Fotos`, `THUMBNAILS_DIR=Miniaturas`.

Notes:

- The 3 `.env` emails are re-asserted as admins on every boot; the admin panel can also pre-create users by email and change roles.
- **Google OAuth** (optional): register the project in Google Cloud with the legal URLs (`FRONTEND_URL/privacidad` and `/terminos`; the homepage must link to them). Google only accepts `localhost` or public domains as `redirect_uri` (never private IPs); on a LAN use `FRONTEND_URL=http://localhost:8080` and let phones hit the API via CORS (`CORS_ALLOWED_ORIGINS`).
- **Google Drive** (optional): enable the Google Drive API and declare the `drive.file` scope (non-sensitive, no verification); the app must be **"In production"** on the consent screen (in "Testing", refresh tokens expire after 7 days).
- **Frontend**: no `.env` of its own — the API is relative and in dev Vite proxies `/api` to `VITE_PROXY_TARGET` (default `http://localhost:8000`; the dev compose uses `http://backend:8000`).
- **Interactive API docs**: FastAPI serves Swagger UI at `GET /docs` and ReDoc at `/redoc` (both reachable through the proxy in production).

## Tests & CI/CD

| Suite | Command | Coverage |
|---|---|---|
| Backend (174) | `cd backend && python -m pytest -q` | Services (validation/thumbnails/HEIC/ZIP/rate-limit), APIs (gallery, auth, admin, secret photographer), Drive and migrations |
| Frontend (77) | `cd frontend && npm test` | utils/api, hooks (`usePhotoSelection`, `useLongPress`) and components |
| Lint/build | `npm run lint` · `npm run build` | oxlint + production build |

- The backend suite is **self-contained**: no `.env` needed and real data is never touched (temp DB/folders). Details in [`tests.md`](tests.md).
- **CI** (`.github/workflows/ci.yml`): PRs to `master`/`main` and pushes to `test/**` → pytest (Python 3.13) + lint/test/build (Node 20).
- **CD** (`.github/workflows/cd.yml`): push to `master` or a `v*` tag → same tests (gating) + build/push of the images to GHCR (`latest`, `sha-…`, semver).

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — system architecture (12 Mermaid diagrams: overview, ER, use cases, sequences, states, components), REST API reference, business rules, technical decisions and repository layout · [Español](ARCHITECTURE.es.md)
- **[tests.md](tests.md)** — backend/frontend test-suite guide (how isolation works, how to run them)
- **[AGENTS.md](AGENTS.md)** — conventions for AI coding agents working on this repo

## Contributing

Contributions are welcome!

1. Open an **issue** to discuss the change (bugs, ideas, questions).
2. **Fork** the repo and create a branch (`feature/...` or `test/...`).
3. Make sure everything is green before the PR:
   ```bash
   (cd backend && python -m pytest -q) && (cd frontend && npm test && npm run lint)
   ```
4. Open a **PR against `master`**; CI must pass.
5. If behavior changes, keep `README.md`, `README.es.md` and `tests.md` in sync.

Commit messages: short and descriptive.

## License

Released under the [MIT License](LICENSE).

## Author

[@juniornff](https://github.com/juniornff)
