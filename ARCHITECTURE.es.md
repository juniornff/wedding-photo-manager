# Arquitectura y referencia de API

← [Volver al README](README.es.md) · [English](ARCHITECTURE.md) | **Español**

Referencia técnica de Wedding Photo Manager: visión general del sistema, modelo ER, diagramas de casos de uso/secuencia/estado, componentes del backend, API REST, reglas de negocio, directorios de fotos, decisiones técnicas y estructura del repositorio.

## Contents

- [Arquitectura](#arquitectura)
- [API](#api)
- [Reglas de negocio](#reglas-de-negocio)
- [Directorios de fotos](#directorios-de-fotos)
- [Decisiones técnicas](#decisiones-técnicas)
- [Estructura del repo](#estructura-del-repo)

## Arquitectura

### Sistema general

```mermaid
graph TB
    subgraph Frontend
        REACT[React + Vite]
        TAILWIND[TailwindCSS]
        SSE[SSE Client]
        EVENT_SRC[EventSource propio del dashboard]
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
    EVENT_SRC -->|SSE sin login| SSE_SRV
    FASTAPI --> SQLA
    SQLA --> DB
    FASTAPI --> FS_SRC
    FASTAPI --> FS_THUMB
    FASTAPI -->|OAuth| GOOGLE
```

### Módulos

```mermaid
graph LR
    MAIN[Módulo Principal<br/>Subida / Galería / Info boda]
    FS[Módulo Fotógrafo Secreto<br/>Retos por mesa / QR / Dashboard público]
    ADMIN[Módulo Admin<br/>Panel de novios]

    MAIN --> FS
    ADMIN --> MAIN
    ADMIN --> FS
```

### Entidad-Relación (base de datos)

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

    User ||--o{ GalleryPhoto : "sube"
    User ||--o{ ChallengePhoto : "sube"
    User }o--o| Table : "asignado a"
    Table ||--o{ Challenge : "tiene"
    Challenge ||--o{ ChallengePhoto : "recibe"
```

> `Table.name` no es único (solo `qr_code`). Los cambios de esquema se aplican con `Base.metadata.create_all` + `ALTER TABLE` manuales en el lifespan (sin Alembic).

### Casos de uso

```mermaid
graph TB
    INVITADO[Invitado]
    NOVIOS[Novios]
    GOOGLE[Usuario Google OAuth]
    ESPECTADOR[Invitado espectador]

    subgraph "Módulo Principal"
        UC1[Ver info boda]
        UC2[Ver carrusel]
        UC3[Subir foto + mensaje]
        UC4[Ver galería en vivo]
        UC5[Descargar foto]
    end

    subgraph "Fotógrafo Secreto"
        UC6[Escanear QR mesa]
        UC7[Ver retos de mesa]
        UC8[Subir foto + mensaje para reto]
        UC9[Ver mi propia foto por reto]
        UC10[Ver tablero público en vivo]
    end

    subgraph "Admin"
        UC11[Gestionar carrusel]
        UC12[Editar info boda]
        UC13[Cambiar colores]
        UC14[Administrar mesas]
        UC15[Crear/editar/desbloquear retos]
        UC16[Gestionar fotos de retos]
        UC17[Elegir mesa ganadora]
        UC18[Quitar mesa ganadora]
        UC19[Moderar galería]
        UC20[Gestionar usuarios: renombrar, mesa, borrar]
    end

    INVITADO --> UC1
    INVITADO --> UC2
    INVITADO --> UC3
    INVITADO --> UC4
    INVITADO --> UC5
    INVITADO --> UC6
    INVITADO --> UC7
    INVITADO --> UC8
    INVITADO --> UC9

    ESPECTADOR --> UC10

    NOVIOS --> UC11
    NOVIOS --> UC12
    NOVIOS --> UC13
    NOVIOS --> UC14
    NOVIOS --> UC15
    NOVIOS --> UC16
    NOVIOS --> UC17
    NOVIOS --> UC18
    NOVIOS --> UC19
    NOVIOS --> UC20

    GOOGLE -->|Recupera identidad| UC3
    GOOGLE -->|Recupera identidad| UC8
```

### Diagramas de secuencia

#### Acceso de invitado y subida de foto

```mermaid
sequenceDiagram
    participant C as Cliente (Browser)
    participant API as FastAPI
    participant DB as SQLite
    participant FS as Filesystem

    Note over C: Primera visita
    C->>API: GET /api/wedding-info
    API->>DB: SELECT wedding_info
    DB-->>API: datos boda
    API-->>C: novios, fecha, colores

    Note over C: localStorage check
    C->>C: ¿UUID exists?
    alt No UUID
        C->>API: POST /api/guest { alias }
        API->>API: Generar uuid4 aleatorio
        API->>DB: INSERT user
        DB-->>API: user_id
        API-->>C: user_id, uuid
        C->>C: Guardar UUID en localStorage
    end

    Note over C: Subir foto
    C->>API: POST /api/gallery/upload { file, message, user_id }
    API->>API: Validar MIME + extensión
    API->>API: Generar UUID filename
    API->>FS: Guardar original en Fotos/Galeria/
    API->>FS: Generar thumbnail en Miniaturas/Galeria/
    API->>DB: INSERT gallery_photo
    DB-->>API: photo_id
    API-->>C: photo_id, url, thumbnail_url
    API-->>C: SSE new_photo { photo_id }
```

#### Fotógrafo Secreto (participante)

```mermaid
sequenceDiagram
    participant C as Participante (Browser)
    participant API as FastAPI
    participant DB as SQLite

    Note over C: Escanea QR de mesa
    C->>API: GET /api/secret-photographer/table/{qr_code}?user_id=X
    API->>DB: Asigna mesa al usuario si es primera vez
    API->>DB: SELECT table + challenges + my_photo por reto
    DB-->>API: challenges 1..N con my_photo
    API-->>C: table + challenges con my_photo

    Note over C: Participante elige reto
    alt Ya subió su foto
        C->>C: Muestra su foto + mensaje + lightbox (no ve fotos ajenas)
    else Reto bloqueado
        C->>C: Este reto está completo
    else Puede subir
        C->>API: POST /api/secret-photographer/upload { file, user_id, message }
        alt Ya subió foto para este reto
            API-->>C: 409 Ya subiste una foto
        else count >= max_photos
            API-->>C: 409 Reto con máximo de fotos
        else
            API-->>C: 201 photo_id
        end
    end

    API-->>C: SSE new_challenge_photo { photo_id, challenge_id, table_id }
```

#### Dashboard público (espectador)

```mermaid
sequenceDiagram
    participant E as Espectador (Browser)
    participant API as FastAPI

    E->>API: GET /api/secret-photographer/dashboard
    API-->>E: winner + tables con challenges y fotos

    Note over E: EventSource propio sin login a /api/events
    E->>API: SSE new_challenge_photo
    E->>E: Refetch dashboard + anima miniaturas nuevas
    E->>API: SSE challenge_photo_deleted
    E->>E: Refetch dashboard
    E->>API: SSE winner_selected
    E->>E: Refetch dashboard + confetti y resaltado del ganador
```

#### Elección de ganador (Admin)

```mermaid
sequenceDiagram
    participant A as Admin (Browser)
    participant API as FastAPI
    participant DB as SQLite

    A->>API: GET /api/admin/tables (auth required)
    API->>DB: SELECT tables + photo_counts
    DB-->>API: table list
    API-->>A: tables

    alt Seleccionar ganador
        A->>API: POST /api/admin/select-winner?table_id=N
        API->>DB: UPDATE wedding_info SET winner_table_id = N
        DB-->>API: success
        API-->>A: message + table_id
        API-->>A: SSE winner_selected { table_id }
    else Quitar ganador
        A->>API: DELETE /api/admin/select-winner
        API->>DB: UPDATE wedding_info SET winner_table_id = NULL
        DB-->>API: success
        API-->>A: message + table_id null
        API-->>A: SSE winner_selected { table_id null }
    end
```

### Estados

#### Ciclo de vida de una foto

```mermaid
stateDiagram-v2
    [*] --> Pendiente: Usuario selecciona archivo
    Pendiente --> Validando: Envía a servidor
    Validando --> Rechazada: MIME inválido
    Validando --> Rechazada: Extensión no permitida
    Validando --> Almacenando: Validación exitosa
    Almacenando --> ConThumbnail: Thumbnail generado
    ConThumbnail --> Visible: Guardada en DB
    Visible --> Eliminada: Admin la elimina
    Eliminada --> [*]
```

#### Ciclo de vida del juego Fotógrafo Secreto

```mermaid
stateDiagram-v2
    [*] --> Preparacion: Admin crea mesas + retos
    Preparacion --> Activo: Admin activa módulo
    Activo --> Completando: Participantes suben fotos
    Completando --> Cerrado: Admin cierra juego
    Cerrado --> Votacion: Admin revisa fotos
    Votacion --> Finalizado: Admin elige ganador
    Finalizado --> Activo: Admin deselecciona ganador (reabre el juego)
```

### Componentes del backend

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

### Eventos SSE emitidos por el backend

| Evento | Emisor | Payload |
|---|---|---|
| `new_photo` | `POST /api/gallery/upload` | `{ photo_id }` |
| `gallery_photo_deleted` | `DELETE /api/admin/gallery/{id}` (y al borrar usuario con `delete_photos=true`) | `{ photo_id }` |
| `new_challenge_photo` | `POST /api/secret-photographer/upload` | `{ photo_id, challenge_id, table_id }` |
| `challenge_photo_deleted` | `DELETE /api/admin/challenges/{cid}/photos/{pid}` (y al borrar usuario con `delete_photos=true`) | `{ photo_id, challenge_id }` |
| `carousel_updated` | Admin carrusel (upload/delete/reorder) | `{}` |
| `info_updated` | `PUT /api/admin/wedding-info` | `WeddingInfoResponse` completo |
| `winner_selected` | Admin seleccionar/quitar ganador | `{ table_id }` o `{ table_id: null }` |

> El dashboard público abre su propio `EventSource` a `/api/events` (sin auth) para `new_challenge_photo`, `challenge_photo_deleted` y `winner_selected`.

### Rutas y componentes del frontend

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
        SD_GRID[Grilla de mesas/retos/fotos]
        SD_LIGHTBOX[PhotoLightbox]
        SD_CONFETTI[Confetti + banner ganador]
    end

    subgraph "FotografoSecretoPage"
        CHAL_LIST[Retos de la mesa]
        FS_UPLOAD[PhotoUpload]
        FS_LIGHTBOX[PhotoLightbox my_photo]
    end

    subgraph "AdminPage [tabs]"
        TAB_DASH[Dashboard]
        TAB_INFO[Info Boda]
        TAB_CARRUSEL[Carrusel]
        TAB_TABLES[Mesas + modal QR]
        TAB_RETOS[Retos]
        TAB_GALERIA[Galería]
        TAB_USERS[Usuarios]
        TAB_WINNER[Ganador]
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

> Swagger UI interactivo: **`GET /docs`** (y ReDoc en `/redoc`), servidos por FastAPI.

| Método | Ruta | Auth | Uso |
|---|---|---|---|
| GET | `/api/wedding-info` | No | Info boda + ganador |
| GET | `/api/carousel` | No | Fotos de carrusel |
| GET | `/api/gallery` | No | Galería (paginación offset/limit) |
| POST | `/api/gallery/upload` | No (rate limit) | Subir foto + mensaje |
| GET | `/api/gallery/{id}/download` | No | Descargar una foto |
| POST | `/api/gallery/batch-download` | No | Descargar varias en ZIP (máx. 100 ids) |
| POST | `/api/guest`, `GET /api/guest/me` | No | Alta/consulta de invitado anónimo |
| GET | `/api/google`, `/api/google/callback` | No | OAuth Google (`?user_id=X` vincula, `&drive=1` consentimiento incremental Drive) |
| GET | `/api/drive/status?user_id=X` | No | `{google_linked, drive_ready}` |
| POST | `/api/drive/save-batch` | No (rate limit) | Guardar hasta 100 fotos en Drive en segundo plano (`{job_id, total}`) |
| GET | `/api/drive/job/{job_id}?user_id=X` | No | Estado del lote Drive |
| POST | `/api/admin/login`, `/api/logout` | — | Sesión admin |
| GET | `/api/admin/me` | Admin | Sesión/identidad del admin |
| GET | `/api/events` | No | SSE |
| GET | `/api/secret-photographer/dashboard` | No | Tablero público en vivo |
| GET | `/api/secret-photographer/table/{qr}` | No | Mesa + retos + my_photo |
| GET | `/api/secret-photographer/my-table?user_id=X` | No | Mesa del usuario o `null` |
| POST | `/api/secret-photographer/upload` | No (rate limit) | Subir foto de reto + mensaje |
| POST | `/api/secret-photographer/batch-download` | No | ZIP de fotos de retos (`Mesa-XX/…`, máx. 100 ids) |
| GET | `/api/secret-photographer/challenge/{id}` | No | Detalle reto (blocked) |
| GET | `/api/admin/dashboard` | Admin | Totales (fotos, usuarios, mesas, retos, carrusel) |
| GET/POST/PUT/DELETE | `/api/admin/tables` | Admin | Gestión mesas |
| GET | `/api/admin/tables/{id}/photos` | Admin | Fotos por mesa (vista ganador) |
| GET/POST/PUT/DELETE | `/api/admin/challenges` | Admin | Gestión retos |
| PUT | `/api/admin/challenges/{id}/unlock` | Admin | Desbloquear reto para editar/eliminar |
| GET | `/api/admin/challenges/{id}/photos` | Admin | Fotos de un reto |
| DELETE | `/api/admin/challenges/{id}/photos/{pid}` | Admin | Borrar foto de reto |
| POST/DELETE | `/api/admin/select-winner` | Admin | Elegir/quitar ganador |
| GET/POST/DELETE | `/api/admin/carousel` | Admin | Gestión carrusel |
| PUT | `/api/admin/carousel/reorder` | Admin | Reordenar carrusel |
| DELETE | `/api/admin/gallery/{id}` | Admin | Borrar foto de galería |
| PUT | `/api/admin/wedding-info` | Admin | Editar info boda/colores |
| GET/POST/DELETE | `/api/admin/users` | Admin | Gestión usuarios (rol, alias, mesa, borrar) |
| PATCH | `/api/admin/users/{id}/role` | Admin | Cambiar rol admin/invitado |
| PUT | `/api/admin/users/{id}` | Admin | Renombrar alias |
| PATCH | `/api/admin/users/{id}/table` | Admin | Asignar/quitar mesa |
| DELETE | `/api/admin/users/{id}?delete_photos=false` | Admin | Borrar usuario; `false` anonimiza fotos, `true` las elimina |

## Reglas de negocio

- Los invitados **no necesitan login**: identidad anónima por UUID en localStorage; el UUID lo genera el **servidor** (uuid4) y se guarda en DB
- **Google OAuth** (opcional) permite recuperar la identidad entre dispositivos; al vincular, el alias se reemplaza por el nombre de Google y se muestra su foto de perfil
- Validación de subida por **MIME type real** (inspección de bytes) + extensión; **todos los formatos** (HEIC/HEIF de iPhone se convierten a JPEG con `exif_transpose`; el original no se conserva); máx. **25 MB**
- Archivos nombrados con **UUID** (sin colisiones); **miniaturas** en caja máxima 150×150 (aspect ratio preservado)
- **Paginación infinita** (offset/limit)
- **Descarga múltiple por selección** (galería, admin y dashboard de retos): se activa **manteniendo presionada** una foto (~500 ms) y se desactiva al quedarse sin selección → **ZIP único** (máx. 100; temporal, se borra tras enviarse) o **archivos individuales** (sin límite)
- **Guardar en Google Drive** (solo usuarios con Google vinculado): consentimiento incremental `drive.file` la primera vez, refresh token por usuario, carpeta `Fotos Boda {novio1} y {novio2}` (los retos replican `Fotografo-Secreto/Mesa-XX`), omite duplicados, jobs en segundo plano con sondeo y avisos por toast
- **15 subidas/minuto** por usuario (también en retos)
- Las fotos se sirven vía FastAPI (sin auth para visualizar)
- Mensaje opcional de **150 caracteres** en galería y en fotos de retos
- Fotógrafo Secreto: **1 foto/usuario/reto** (unique constraint), máx = nº de participantes de la mesa; el reto se bloquea al llenarse (el admin puede desbloquearlo para editar/eliminar)
- Un usuario se asigna a una **mesa una sola vez**; cada participante ve **solo su propia foto** por reto; los espectadores ven todo en el dashboard público
- **Admin**: usuarios con `role='admin'` (sin modelo aparte); los 3 emails del `.env` se reafirman como admin en cada arranque; el panel puede pre-crear usuarios por email y cambiar roles; un login de Google con correo admin **fusiona** la identidad de invitado previa (fotos + mesa)
- Al borrar un usuario, sus fotos pueden quedar **anónimas** (`user_id=NULL` → "Anónimo") o **eliminarse** con sus archivos
- `Miniaturas/` replica la estructura de `Fotos/`; limpieza de huérfanos cada 10 s; SQLite con **WAL mode** (sin backups automáticos)

## Directorios de fotos

```
Fotos/
├── Carrucel/          # Carrusel de los novios
├── Galeria/           # Fotos subidas por invitados
└── Fotografo-Secreto/
    ├── Mesa-01/       # QR.png + fotos de retos de la mesa 1
    ├── Mesa-02/
    └── ...

Miniaturas/            # Misma estructura, miniaturas 150×150
```

## Decisiones técnicas

| Aspecto | Decisión |
|---|---|
| Gestión de estado | React Context |
| Cliente HTTP | `fetch` nativo + helpers `api()`/`apiUpload()`/`apiBlob()` |
| Paginación | offset/limit |
| Imágenes | Pillow (Python) |
| OAuth | Authlib |
| Google Drive | REST v3 con `httpx` (sin SDK) |
| QR | `qrcode` (Python) |
| Migraciones BD | `create_all` + `ALTER TABLE` manuales en el lifespan (sin Alembic) |
| Config | pydantic-settings |
| Tiempo real | SSE (7 eventos nombrados) |
| Lightbox | Componente compartido `PhotoLightbox` |
| Versionado | Tags `vX.Y.Z` → imágenes GHCR versionadas (rollback con `TAG`) |

## Estructura del repo

```
wedding-photo-manager/
├── backend/                  # FastAPI (app/, tests/, Dockerfile)
│   └── app/
│       ├── routers/          # main, auth, fotografo_secreto, admin, drive, sse
│       ├── services/         # photo_service, drive_service, auth_service, sse_manager…
│       ├── models/  schemas/ # modelos SQLAlchemy + schemas pydantic
│       └── main.py           # app, lifespan (migraciones), mounts
├── frontend/                 # React + Vite (src/, Dockerfile, Dockerfile.dev, nginx.conf.template)
├── docs/screenshots/         # Capturas de este README
├── .github/workflows/        # ci.yml (tests) + cd.yml (imágenes GHCR)
├── docker-compose.yml        # Despliegue: pull de imágenes GHCR
├── docker-compose.dev.yml    # Desarrollo: build desde código fuente
├── tests.md                  # Guía de la suite de tests
├── AGENTS.md                 # Guía para agentes de IA
└── README.es.md              # Esta versión en español
```

En ejecución se crean `Fotos/`, `Miniaturas/` y `data/` (ignorados por git).

