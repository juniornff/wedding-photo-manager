# Architecture & API Reference

← [Back to README](README.md) · **English** | [Español](ARCHITECTURE.es.md)

Technical reference of Wedding Photo Manager: system overview, ER model, use-case/sequence/state diagrams, backend components, REST API, business rules, photo directories, technical decisions and repository layout.

## Contents

- [Architecture](#architecture)
- [API](#api)
- [Business rules](#business-rules)
- [Photo directories](#photo-directories)
- [Technical decisions](#technical-decisions)
- [Project structure](#project-structure)

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

