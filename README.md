# Wedding Photo Manager

[![CI](https://github.com/juniornff/wedding-photo-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/juniornff/wedding-photo-manager/actions/workflows/ci.yml)
[![CD](https://github.com/juniornff/wedding-photo-manager/actions/workflows/cd.yml/badge.svg)](https://github.com/juniornff/wedding-photo-manager/actions/workflows/cd.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-174%20backend%20%2B%2077%20frontend-blue.svg)](#tests--ciud)

Web application to manage wedding photos: guests upload, browse and download photos **without signing up**, while the couple enjoys the interactive **Secret Photographer** game (per-table challenges with QR codes) and a full admin panel.

**English** | [Español](README.es.md)

![Main page](docs/screenshots/main.png)

## Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Use it for your wedding](#use-it-for-your-wedding)
- [Configuration (.env)](#configuration-env)
- [Architecture](#architecture)
- [API](#api)
- [Business rules](#business-rules)
- [Photo directories](#photo-directories)
- [Tests & CI/CD](#tests--ciud)
- [Technical decisions](#technical-decisions)
- [Project structure](#project-structure)
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

Images are published to GitHub Container Registry on every push to `master` (`ghcr.io/juniornff/wedding-photo-manager-backend|-frontend`). Being private, they require authentication first:

```bash
docker login ghcr.io          # username + PAT with read:packages
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

## Architecture

### System overview

```mermaid
graph TB
    subgraph Frontend
        REACT[React + Vite]
        TAILWIND[TailwindCSS]
        SSE[SSE Client]
        EVENT_SRC[Dashboard own EventSource]
    end

    subgraph Backend
        FASTAPI[FastAPI]
        SQLA[SQLAlchemy Async]
        SSE_SRV[SSE Endpoint /api/events]
    end

    subgraph Storage
        DB[(SQLite)]
        FS_SRC[Fotos/]
        FS_THUMB[Miniaturas/]
    end

    subgraph External
        GOOGLE[Google OAuth]
    end

    REACT -->|HTTP/REST| FASTAPI
    REACT -->|SSE| SSE_SRV
    EVENT_SRC -->|SSE no login| SSE_SRV
    FASTAPI --> SQLA
    SQLA --> DB
    FASTAPI --> FS_SRC
    FASTAPI --> FS_THUMB
    FASTAPI -->|OAuth| GOOGLE
```

### Modules

```mermaid
graph LR
    MAIN[Main module<br/>Upload / Gallery / Wedding info]
    FS[Secret Photographer<br/>Per-table challenges / QR / Live dashboard]
    ADMIN[Admin module<br/>Control panel]

    MAIN --> FS
    ADMIN --> MAIN
    ADMIN --> FS
```

### Entity-Relationship (database)

```mermaid
erDiagram
    User {
        int id PK
        string uuid UK
        string alias
        string google_id UK
        string google_name
        string google_photo
        string google_refresh_token
        string email UK
        string password_hash
        string role
        int table_id FK
        datetime created_at
    }

    WeddingInfo {
        int id PK
        string novio1_name
        string novio2_name
        date wedding_date
        string message
        string color_scheme
        int carousel_interval
        int winner_table_id FK
        datetime updated_at
    }

    CarouselPhoto {
        int id PK
        string uuid UK
        string path
        string thumbnail_path
        int sort_order
        datetime uploaded_at
    }

    GalleryPhoto {
        int id PK
        string uuid UK
        string path
        string thumbnail_path
        string message
        int user_id FK
        datetime uploaded_at
    }

    Table {
        int id PK
        string name
        string qr_code UK
        datetime created_at
    }

    Challenge {
        int id PK
        int table_id FK
        string description
        int sort_order
        boolean locked
        datetime created_at
    }

    ChallengePhoto {
        int id PK
        string uuid UK
        string path
        string thumbnail_path
        string message
        int challenge_id FK
        int user_id FK
        datetime uploaded_at
    }

    User ||--o{ GalleryPhoto : "uploads"
    User ||--o{ ChallengePhoto : "uploads"
    User }o--o| Table : "assigned to"
    Table ||--o{ Challenge : "has"
    Challenge ||--o{ ChallengePhoto : "receives"
```

> `Table.name` is not unique (only `qr_code` is). Schema changes are applied with `Base.metadata.create_all` plus hand-written `ALTER TABLE` statements in the lifespan (no Alembic).

### Use cases

```mermaid
graph TB
    GUEST[Guest]
    COUPLE[Couple]
    GOOGLE[Google OAuth user]
    VIEWER[Guest viewer]

    subgraph "Main module"
        UC1[View wedding info]
        UC2[View carousel]
        UC3[Upload photo + message]
        UC4[View live gallery]
        UC5[Download photo]
    end

    subgraph "Secret Photographer"
        UC6[Scan table QR]
        UC7[View table challenges]
        UC8[Upload photo + message for a challenge]
        UC9[View my own photo per challenge]
        UC10[View public live dashboard]
    end

    subgraph "Admin"
        UC11[Manage carousel]
        UC12[Edit wedding info]
        UC13[Change colors]
        UC14[Manage tables]
        UC15[Create/edit/unlock challenges]
        UC16[Manage challenge photos]
        UC17[Pick winning table]
        UC18[Remove winning table]
        UC19[Moderate gallery]
        UC20[Manage users: rename, table, delete]
    end

    GUEST --> UC1
    GUEST --> UC2
    GUEST --> UC3
    GUEST --> UC4
    GUEST --> UC5
    GUEST --> UC6
    GUEST --> UC7
    GUEST --> UC8
    GUEST --> UC9

    VIEWER --> UC10

    COUPLE --> UC11
    COUPLE --> UC12
    COUPLE --> UC13
    COUPLE --> UC14
    COUPLE --> UC15
    COUPLE --> UC16
    COUPLE --> UC17
    COUPLE --> UC18
    COUPLE --> UC19
    COUPLE --> UC20

    GOOGLE -->|Recovers identity| UC3
    GOOGLE -->|Recovers identity| UC8
```

### Sequence diagrams

#### Guest access and photo upload

```mermaid
sequenceDiagram
    participant C as Client (Browser)
    participant API as FastAPI
    participant DB as SQLite
    participant FS as Filesystem

    Note over C: First visit
    C->>API: GET /api/wedding-info
    API->>DB: SELECT wedding_info
    DB-->>API: wedding data
    API-->>C: names, date, colors

    Note over C: localStorage check
    C->>C: UUID exists?
    alt No UUID
        C->>API: POST /api/guest with alias
        API->>API: Generate random uuid4
        API->>DB: INSERT user
        DB-->>API: user_id
        API-->>C: user_id and uuid
        C->>C: Store UUID in localStorage
    end

    Note over C: Upload photo
    C->>API: POST /api/gallery/upload with file, message, user_id
    API->>API: Validate MIME + extension
    API->>API: Generate UUID filename
    API->>FS: Save original to Fotos/Galeria/
    API->>FS: Generate thumbnail in Miniaturas/Galeria/
    API->>DB: INSERT gallery_photo
    DB-->>API: photo_id
    API-->>C: photo_id, url, thumbnail_url
    API-->>C: SSE new_photo with photo_id
```

#### Secret Photographer (participant)

```mermaid
sequenceDiagram
    participant C as Participant (Browser)
    participant API as FastAPI
    participant DB as SQLite

    Note over C: Scans table QR
    C->>API: GET /api/secret-photographer/table/{qr_code}?user_id=X
    API->>DB: Assign table to user on first visit
    API->>DB: SELECT table + challenges + my_photo per challenge
    DB-->>API: challenges 1..N with my_photo
    API-->>C: table + challenges with my_photo

    Note over C: Participant picks a challenge
    alt Already uploaded my photo
        C->>C: Shows my photo + message + lightbox (never sees others)
    else Challenge locked
        C->>C: This challenge is full
    else Can upload
        C->>API: POST /api/secret-photographer/upload with file, user_id, message
        alt Already uploaded for this challenge
            API-->>C: 409 you already uploaded a photo
        else count >= max_photos
            API-->>C: 409 challenge photo limit reached
        else
            API-->>C: 201 photo_id
        end
    end

    API-->>C: SSE new_challenge_photo with photo_id, challenge_id, table_id
```

#### Public dashboard (viewer)

```mermaid
sequenceDiagram
    participant E as Viewer (Browser)
    participant API as FastAPI

    E->>API: GET /api/secret-photographer/dashboard
    API-->>E: winner + tables with challenges and photos

    Note over E: Own EventSource without login to /api/events
    E->>API: SSE new_challenge_photo
    E->>E: Refetch dashboard + animate new thumbnails
    E->>API: SSE challenge_photo_deleted
    E->>E: Refetch dashboard
    E->>API: SSE winner_selected
    E->>E: Refetch dashboard + confetti and winner highlight
```

#### Winner selection (Admin)

```mermaid
sequenceDiagram
    participant A as Admin (Browser)
    participant API as FastAPI
    participant DB as SQLite

    A->>API: GET /api/admin/tables (auth required)
    API->>DB: SELECT tables + photo_counts
    DB-->>API: table list
    API-->>A: tables

    alt Select winner
        A->>API: POST /api/admin/select-winner?table_id=N
        API->>DB: UPDATE wedding_info SET winner_table_id = N
        DB-->>API: success
        API-->>A: message + table_id
        API-->>A: SSE winner_selected with table_id
    else Remove winner
        A->>API: DELETE /api/admin/select-winner
        API->>DB: UPDATE wedding_info SET winner_table_id = NULL
        DB-->>API: success
        API-->>A: message + table_id null
        API-->>A: SSE winner_selected with null table_id
    end
```

### State diagrams

#### Photo lifecycle

```mermaid
stateDiagram-v2
    [*] --> Pending: User picks a file
    Pending --> Validating: Sent to server
    Validating --> Rejected: Invalid MIME
    Validating --> Rejected: Disallowed extension
    Validating --> Storing: Validation passed
    Storing --> WithThumbnail: Thumbnail generated
    WithThumbnail --> Visible: Saved in DB
    Visible --> Deleted: Admin deletes it
    Deleted --> [*]
```

#### Secret Photographer game lifecycle

```mermaid
stateDiagram-v2
    [*] --> Setup: Admin creates tables + challenges
    Setup --> Active: Admin activates the game
    Active --> Playing: Participants upload photos
    Playing --> Closed: Admin closes the game
    Closed --> Reviewing: Admin reviews photos
    Reviewing --> Finished: Admin picks the winner
    Finished --> Active: Admin deselects the winner (reopens the game)
```

### Backend components

```mermaid
classDiagram
    class FastAPIApp {
        +include_routers()
        +static_mounts()
        +create_schema()
        +alter_table_manual()
    }

    class MainRouter {
        +get_wedding_info()
        +list_carousel()
        +list_gallery()
        +upload_photo()
        +download_photo()
        +batch_download()
    }

    class SecretPhotographerRouter {
        +get_dashboard()
        +get_table_by_qr()
        +get_my_table()
        +get_challenge()
        +batch_download_challenge_photos()
        +upload_challenge_photo()
    }

    class AdminRouter {
        +get_me()
        +update_wedding_info()
        +manage_carousel()
        +manage_gallery()
        +manage_tables()
        +manage_challenges()
        +unlock_challenge()
        +list_challenge_photos()
        +delete_challenge_photo()
        +manage_users()
        +select_winner()
        +clear_winner()
    }

    class AuthRouter {
        +register_guest()
        +get_guest_me()
        +google_login()
        +google_callback()
        +admin_login()
        +logout()
    }

    class SSERouter {
        +events()
    }

    class DriveRouter {
        +drive_status()
        +drive_save_batch()
        +drive_job()
    }

    class DriveService {
        +check_drive_rate_limit()
        +refresh_access_token()
        +ensure_folder_path()
        +list_file_names()
        +upload_file()
        +start_drive_batch()
    }

    class PhotoService {
        +validate_file()
        +save_photo()
        +generate_thumbnail()
        +delete_photo()
        +check_rate_limit()
    }

    class AuthService {
        +create_guest()
        +verify_password()
        +init_admin()
    }

    class SSEManager {
        +register()
        +unregister()
        +broadcast(event, data)
    }

    class Serializers {
        +wedding_info_response()
        +challenge_photo_response()
        +counts_by_challenge()
        +counts_by_table()
    }

    FastAPIApp --> MainRouter
    FastAPIApp --> SecretPhotographerRouter
    FastAPIApp --> AdminRouter
    FastAPIApp --> AuthRouter
    FastAPIApp --> DriveRouter
    FastAPIApp --> SSERouter

    MainRouter --> PhotoService
    SecretPhotographerRouter --> PhotoService
    AdminRouter --> PhotoService
    AuthRouter --> AuthService
    DriveRouter --> DriveService

    MainRouter --> Serializers
    SecretPhotographerRouter --> Serializers
    AdminRouter --> Serializers

    MainRouter --> SSEManager
    SecretPhotographerRouter --> SSEManager
    AdminRouter --> SSEManager
```

### SSE events emitted by the backend

| Event | Emitted by | Payload |
|---|---|---|
| `new_photo` | `POST /api/gallery/upload` | `{ photo_id }` |
| `gallery_photo_deleted` | `DELETE /api/admin/gallery/{id}` (also when deleting a user with `delete_photos=true`) | `{ photo_id }` |
| `new_challenge_photo` | `POST /api/secret-photographer/upload` | `{ photo_id, challenge_id, table_id }` |
| `challenge_photo_deleted` | `DELETE /api/admin/challenges/{cid}/photos/{pid}` (also when deleting a user with `delete_photos=true`) | `{ photo_id, challenge_id }` |
| `carousel_updated` | Admin carousel ops (upload/delete/reorder) | `{}` |
| `info_updated` | `PUT /api/admin/wedding-info` | Full `WeddingInfoResponse` |
| `winner_selected` | Admin select/deselect winner | `{ table_id }` or `{ table_id: null }` |

> The public dashboard opens its own `EventSource` against `/api/events` (no auth) for `new_challenge_photo`, `challenge_photo_deleted` and `winner_selected`.

### Frontend routes and components

```mermaid
graph TB
    APP[App]
    NAVBAR[Navbar]
    MAIN[MainPage /]
    SECRET_DASH[SecretDashboardPage /fotografo-secreto]
    FS_PAGE[FotografoSecretoPage /fotografo-secreto/:qr_code]
    ADMIN_PAGE[AdminPage /admin]

    PUB_LIGHTBOX[PhotoLightbox]
    SELECT_UI[SelectionToolbar + DownloadDialog]

    subgraph "MainPage"
        GRID[PhotoGrid]
        UPLOAD[PhotoUpload]
    end

    subgraph "SecretDashboardPage"
        SD_GRID[Tables/challenges/photos grid]
        SD_LIGHTBOX[PhotoLightbox]
        SD_CONFETTI[Confetti + winner banner]
    end

    subgraph "FotografoSecretoPage"
        CHAL_LIST[Table challenges]
        FS_UPLOAD[PhotoUpload]
        FS_LIGHTBOX[PhotoLightbox my_photo]
    end

    subgraph "AdminPage tabs"
        TAB_DASH[Dashboard]
        TAB_INFO[Wedding info]
        TAB_CARRUSEL[Carousel]
        TAB_TABLES[Tables + QR modal]
        TAB_RETOS[Challenges]
        TAB_GALERIA[Gallery]
        TAB_USERS[Users]
        TAB_WINNER[Winner]
        CHAL_MODAL[ChallengePhotosModal]
    end

    APP --> NAVBAR
    APP --> MAIN
    APP --> SECRET_DASH
    APP --> FS_PAGE
    APP --> ADMIN_PAGE

    MAIN --> GRID
    MAIN --> UPLOAD

    SECRET_DASH --> SD_GRID
    SECRET_DASH --> SD_LIGHTBOX

    FS_PAGE --> CHAL_LIST
    FS_PAGE --> FS_UPLOAD
    FS_PAGE --> FS_LIGHTBOX

    ADMIN_PAGE --> TAB_DASH
    ADMIN_PAGE --> TAB_INFO
    ADMIN_PAGE --> TAB_CARRUSEL
    ADMIN_PAGE --> TAB_TABLES
    ADMIN_PAGE --> TAB_RETOS
    ADMIN_PAGE --> TAB_GALERIA
    ADMIN_PAGE --> TAB_USERS
    ADMIN_PAGE --> TAB_WINNER

    TAB_RETOS --> CHAL_MODAL
    CHAL_MODAL --> PUB_LIGHTBOX

    GRID --> SELECT_UI
    SD_GRID --> SELECT_UI
    TAB_GALERIA --> SELECT_UI
```

## API

> Interactive docs: **`GET /docs`** (Swagger UI) and `/redoc` (ReDoc), served by FastAPI.

| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET | `/api/wedding-info` | No | Wedding info + winner |
| GET | `/api/carousel` | No | Carousel photos |
| GET | `/api/gallery` | No | Gallery (offset/limit pagination) |
| POST | `/api/gallery/upload` | No (rate limit) | Upload photo + message |
| GET | `/api/gallery/{id}/download` | No | Download one photo |
| POST | `/api/gallery/batch-download` | No | Download several as ZIP (max 100 ids) |
| POST | `/api/guest`, `GET /api/guest/me` | No | Create/query anonymous guest |
| GET | `/api/google`, `/api/google/callback` | No | Google OAuth (`?user_id=X` links, `&drive=1` incremental Drive consent) |
| GET | `/api/drive/status?user_id=X` | No | `{google_linked, drive_ready}` |
| POST | `/api/drive/save-batch` | No (rate limit) | Save up to 100 photos to Drive in the background (`{job_id, total}`) |
| GET | `/api/drive/job/{job_id}?user_id=X` | No | Drive batch status |
| POST | `/api/admin/login`, `/api/logout` | — | Admin session |
| GET | `/api/admin/me` | Admin | Admin session/identity |
| GET | `/api/events` | No | SSE |
| GET | `/api/secret-photographer/dashboard` | No | Public live dashboard |
| GET | `/api/secret-photographer/table/{qr}` | No | Table + challenges + my_photo |
| GET | `/api/secret-photographer/my-table?user_id=X` | No | User's table or `null` |
| POST | `/api/secret-photographer/upload` | No (rate limit) | Upload challenge photo + message |
| POST | `/api/secret-photographer/batch-download` | No | ZIP of challenge photos (`Mesa-XX/…`, max 100 ids) |
| GET | `/api/secret-photographer/challenge/{id}` | No | Challenge detail (blocked) |
| GET | `/api/admin/dashboard` | Admin | Totals (photos, users, tables, challenges, carousel) |
| GET/POST/PUT/DELETE | `/api/admin/tables` | Admin | Table management |
| GET | `/api/admin/tables/{id}/photos` | Admin | Photos per table (winner view) |
| GET/POST/PUT/DELETE | `/api/admin/challenges` | Admin | Challenge management |
| PUT | `/api/admin/challenges/{id}/unlock` | Admin | Unlock challenge for editing/deleting |
| GET | `/api/admin/challenges/{id}/photos` | Admin | Photos of a challenge |
| DELETE | `/api/admin/challenges/{id}/photos/{pid}` | Admin | Delete challenge photo |
| POST/DELETE | `/api/admin/select-winner` | Admin | Pick/remove winner |
| GET/POST/DELETE | `/api/admin/carousel` | Admin | Carousel management |
| PUT | `/api/admin/carousel/reorder` | Admin | Reorder carousel |
| DELETE | `/api/admin/gallery/{id}` | Admin | Delete gallery photo |
| PUT | `/api/admin/wedding-info` | Admin | Edit wedding info/colors |
| GET/POST/DELETE | `/api/admin/users` | Admin | User management (role, alias, table, delete) |
| PATCH | `/api/admin/users/{id}/role` | Admin | Change admin/guest role |
| PUT | `/api/admin/users/{id}` | Admin | Rename alias |
| PATCH | `/api/admin/users/{id}/table` | Admin | Assign/clear table |
| DELETE | `/api/admin/users/{id}?delete_photos=false` | Admin | Delete user; `false` anonymizes photos, `true` deletes them |

## Business rules

- Guests **need no account**: anonymous identity via a server-generated UUID (uuid4) stored in DB and localStorage
- **Google OAuth** (optional) recovers identity across devices; when linked, the alias is replaced by the Google name and profile photo
- Uploads validated by **real MIME type** (byte inspection) + extension; **every image format** (iPhone HEIC/HEIF is converted to JPEG with `exif_transpose`; the original is not kept); max **25 MB**
- Files named with a **UUID** (no collisions); **thumbnails** in a max 150×150 box (aspect ratio preserved)
- **Infinite scroll** pagination (offset/limit)
- **Bulk download by selection** (gallery, admin tab and challenge dashboard): activated by **long-pressing** a photo (~500 ms), deactivated when the selection empties → **single ZIP** (max 100; temp file, deleted after sending) or **individual files** (no limit)
- **Save to Google Drive** (only users with linked Google): incremental `drive.file` consent on first use, per-user refresh token, root folder `Fotos Boda {novio1} y {novio2}` (challenges mirror `Fotografo-Secreto/Mesa-XX`), duplicate skipping, background jobs with polling and toast notifications
- **15 uploads/minute** per user (also for challenges)
- Photos are served by FastAPI (no auth to view)
- Optional **150-character** message on gallery and challenge photos
- Secret Photographer: **1 photo/user/challenge** (unique constraint), max = table participant count; challenges lock when full (admins can unlock to edit/delete)
- A user is assigned to a **table exactly once**; each participant sees **only their own photo** per challenge; viewers see everything on the public dashboard
- **Admins** are `User` rows with `role='admin'` (no separate model); the 3 `.env` emails are re-asserted as admins on every boot; the panel can pre-create users by email and change roles; a Google login with an admin email **merges** any previous guest identity (photos + table)
- Deleting a user can leave photos **anonymous** (`user_id=NULL` → "Anónimo") or **remove** them with their files
- `Miniaturas/` mirrors `Fotos/`; orphan cleanup every 10 s; SQLite in **WAL mode** (no automatic backups)

## Photo directories

```
Fotos/
├── Carrucel/          # Couple's carousel
├── Galeria/           # Guest uploads
└── Fotografo-Secreto/
    ├── Mesa-01/       # QR.png + challenge photos for table 1
    ├── Mesa-02/
    └── ...

Miniaturas/            # Same structure, 150×150 thumbnails
```

## Tests & CI/CD

| Suite | Command | Coverage |
|---|---|---|
| Backend (174) | `cd backend && python -m pytest -q` | Services (validation/thumbnails/HEIC/ZIP/rate-limit), APIs (gallery, auth, admin, secret photographer), Drive and migrations |
| Frontend (77) | `cd frontend && npm test` | utils/api, hooks (`usePhotoSelection`, `useLongPress`) and components |
| Lint/build | `npm run lint` · `npm run build` | oxlint + production build |

- The backend suite is **self-contained**: no `.env` needed and real data is never touched (temp DB/folders). Details in [`tests.md`](tests.md).
- **CI** (`.github/workflows/ci.yml`): PRs to `master`/`main` and pushes to `test/**` → pytest (Python 3.13) + lint/test/build (Node 20).
- **CD** (`.github/workflows/cd.yml`): push to `master` or a `v*` tag → same tests (gating) + build/push of the images to GHCR (`latest`, `sha-…`, semver).

## Technical decisions

| Aspect | Decision |
|---|---|
| State management | React Context |
| HTTP client | Native `fetch` + `api()`/`apiUpload()`/`apiBlob()` helpers |
| Pagination | offset/limit |
| Image processing | Pillow (Python) |
| OAuth | Authlib |
| Google Drive | REST v3 via `httpx` (no SDK) |
| QR codes | `qrcode` (Python) |
| DB migrations | `create_all` + hand-written `ALTER TABLE` in the lifespan (no Alembic) |
| Config | pydantic-settings |
| Realtime | SSE (7 named events) |
| Lightbox | Shared `PhotoLightbox` component |
| Versioning | `vX.Y.Z` tags → versioned GHCR images (rollback via `TAG`) |

## Project structure

```
wedding-photo-manager/
├── backend/                  # FastAPI (app/, tests/, Dockerfile)
│   └── app/
│       ├── routers/          # main, auth, fotografo_secreto, admin, drive, sse
│       ├── services/         # photo_service, drive_service, auth_service, sse_manager…
│       ├── models/  schemas/ # SQLAlchemy models + pydantic schemas
│       └── main.py           # app, lifespan (migrations), static mounts
├── frontend/                 # React + Vite (src/, Dockerfile, Dockerfile.dev, nginx.conf.template)
├── docs/screenshots/         # Screenshots used in this README
├── .github/workflows/        # ci.yml (tests) + cd.yml (GHCR images)
├── docker-compose.yml        # Deployment: pulls GHCR images
├── docker-compose.dev.yml    # Development: builds from source
├── tests.md                  # Test-suite guide (Spanish)
├── AGENTS.md                 # Guide for AI coding agents
└── README.es.md              # Spanish version of this README
```

At runtime `Fotos/`, `Miniaturas/` and `data/` are created (git-ignored).

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
