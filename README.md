# Wedding Photo Manager

Aplicación web para gestionar fotos de bodas: subida, visualización y descarga por parte de los invitados, más el módulo interactivo **Fotógrafo Secreto**.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | FastAPI + SQLAlchemy (async) + SQLite (WAL mode) |
| Backend libs | Pillow (thumbnails), Authlib (OAuth), qrcode (QR gen), pydantic-settings (config) |
| Frontend | React 19 + Vite + TailwindCSS v4 + React Router |
| Frontend HTTP | fetch nativo + React Context (sin Redux/axios) |
| Tiempo real | Server-Sent Events (SSE) |
| Almacenamiento | Local filesystem (`Fotos/`, `Miniaturas/`), SQLite en `data/wedding.db` |
| Autenticación | Google OAuth + UUID anónimo (localStorage) |
| Despliegue | Docker Compose (backend + frontend); Caddy aparte |
| Testing | Sin suites por el momento |

---

## Arquitectura del sistema

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

---

## Módulos

```mermaid
graph LR
    MAIN[Módulo Principal<br/>Subida / Galería / Info boda]
    FS[Módulo Fotógrafo Secreto<br/>Retos por mesa / QR / Dashboard público]
    ADMIN[Módulo Admin<br/>Panel de novios]

    MAIN --> FS
    ADMIN --> MAIN
    ADMIN --> FS
```

### Módulo Principal
- Información de la boda (nombres, fecha)
- Carrusel de fotos de los novios (`Fotos/Carrucel/`)
- Galería de fotos subidas por invitados (`Fotos/Galeria/`) — con mensaje opcional (150 caracteres)
- Botón flotante para subir fotos
- Visualización en vivo vía SSE (`new_photo`, `gallery_photo_deleted`, `info_updated`, `carousel_updated`)

### Módulo Fotógrafo Secreto
- Cada mesa tiene un QR único (generado como PNG estático en `Fotos/Fotografo-Secreto/Mesa-XX/QR.png`)
- Retos por mesa (creados desde el panel admin); 1 foto por participante por reto, máximo = nº de participantes de la mesa
- El usuario se asigna a una mesa al escanear el QR (una sola vez, error si reasigna)
- Mensaje opcional (150 caracteres) también en las fotos de reto
- Cada participante ve su **propia foto** por reto (badge "✓ Tu foto subida" + lightbox)
- **Dashboard público** (`/fotografo-secreto`): mesas → retos → fotos con autor, progreso y ganador en vivo, animación de confetti al elegir ganador
- Admin elige *(y puede deseleccionar)* ganador manualmente

### Módulo Admin
- Gestionar carrusel, info de boda, esquema de colores
- Administrar mesas y retos
- Ver/descargar/eliminar fotos de cada reto
- Elegir o quitar la mesa ganadora del Fotógrafo Secreto

---

## Diagrama Entidad-Relación (Base de Datos)

```mermaid
erDiagram
    User {
        int id PK
        string uuid UK
        string alias
        string google_id UK
        string google_name
        string google_photo
        int table_id FK
        datetime created_at
    }

    WeddingInfo {
        int id PK
        string novio1_name
        string novio2_name
        date wedding_date
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

    Admin {
        int id PK
        string email UK
        string password_hash
        datetime created_at
    }

    User ||--o{ GalleryPhoto : "sube"
    User ||--o{ ChallengePhoto : "sube"
    User }o--o| Table : "asignado a"
    Table ||--o{ Challenge : "tiene"
    Challenge ||--o{ ChallengePhoto : "recibe"
```

> Nota: `Table.name` no es único en la BD (solo `qr_code` lo es). Los cambios de esquema se aplican con `Base.metadata.create_all` + `ALTER TABLE` manuales en el lifespan (sin Alembic).

---

## Diagrama de Casos de Uso

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

    GOOGLE -->|Recupera identidad| UC3
    GOOGLE -->|Recupera identidad| UC8
```

---

## Diagramas de Secuencia

### Flujo: Acceso de invitado y subida de foto

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
    API-->>C: { novios, fecha, colores }

    Note over C: localStorage check
    C->>C: ¿UUID exists?
    alt No UUID
        C->>API: POST /api/guest { alias }
        API->>API: Generar uuid4 aleatorio
        API->>DB: INSERT user
        DB-->>API: user_id
        API-->>C: { user_id, uuid }
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
    API-->>C: { photo_id, url, thumbnail_url }
    API-->>C: SSE: new_photo { photo_id }
```

### Flujo: Fotógrafo Secreto (participante)

```mermaid
sequenceDiagram
    participant C as Participante (Browser)
    participant API as FastAPI
    participant DB as SQLite

    Note over C: Escanea QR de mesa
    C->>API: GET /api/secret-photographer/table/{qr_code}?user_id=X
    API->>DB: Asigna mesa al usuario (table_id) si es primera vez
    API->>DB: SELECT table + challenges + my_photo por reto
    DB-->>API: challenges[1..N] con my_photo
    API-->>C: { table, challenges: [{..., my_photo}] }

    Note over C: Participante elige reto
    alt Ya subió su foto
        C->>C: Muestra su foto + mensaje + lightbox (no ve fotos ajenas)
    else Reto bloqueado (max alcanzado)
        C->>C: "Este reto está completo"
    else Puede subir
        C->>API: POST /api/secret-photographer/upload?challenge_id=ID { file, user_id, message }
        alt Ya subió foto para este reto
            API-->>C: 409 { detail: "Ya subiste una foto..." }
        else count >= max_photos
            API-->>C: 409 { detail: "Reto con máximo de fotos" }
        else
            API-->>C: 201 { photo_id }
        end
    end

    API-->>C: SSE: new_challenge_photo { photo_id, challenge_id, table_id }
```

### Flujo: Dashboard público (espectador no participante)

```mermaid
sequenceDiagram
    participant E as Espectador (Browser)
    participant API as FastAPI

    E->>API: GET /api/secret-photographer/dashboard
    API-->>E: { winner_table_id/name, tables:[{challenges:[{photos}]}] }

    Note over E: EventSource propio (sin login) a /api/events
    E->>API: SSE: new_challenge_photo
    E->>E: Refetch dashboard + anima miniaturas nuevas (debounce ~250ms)
    E->>API: SSE: challenge_photo_deleted
    E->>E: Refetch dashboard
    E->>API: SSE: winner_selected
    E->>E: Refetch dashboard + confetti y resaltado del ganador
```

### Flujo: Elección de ganador (Admin)

```mermaid
sequenceDiagram
    participant A as Admin (Browser)
    participant API as FastAPI
    participant DB as SQLite

    A->>API: GET /api/admin/tables (auth required)
    API->>DB: SELECT tables + photo_counts
    DB-->>API: table list
    API-->>A: { tables }

    alt Seleccionar ganador
        A->>API: POST /api/admin/select-winner?table_id=N
        API->>DB: UPDATE wedding_info SET winner_table_id = N
        DB-->>API: success
        API-->>A: { message, table_id }
        API-->>A: SSE: winner_selected { table_id }
    else Quitar ganador
        A->>API: DELETE /api/admin/select-winner
        API->>DB: UPDATE wedding_info SET winner_table_id = NULL
        DB-->>API: success
        API-->>A: { message, table_id: null }
        API-->>A: SSE: winner_selected { table_id: null }
    end
```

---

## Diagrama de Estados

### Ciclo de vida de una foto

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

### Ciclo de vida del juego Fotógrafo Secreto

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

---

## Diagrama de Componentes del Backend

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
        +get_challenge()
        +upload_challenge_photo()
    }

    class AdminRouter {
        +get_me()
        +update_wedding_info()
        +manage_carousel()
        +manage_gallery()
        +manage_tables()
        +manage_challenges()
        +list_challenge_photos()
        +delete_challenge_photo()
        +select_winner()
        +clear_winner()
        +get_table_qr()
    }

    class AuthRouter {
        +register_guest()
        +get_guest_me()
        +google_login()
        +google_callback()
        +admin_login()
        +logout()
    }

    class PhotoService {
        +validate_file()
        +save_photo()
        +generate_thumbnail()
        +delete_photo()
        +check_rate_limit()
    }

    class AuthService {
        +verify_admin_emails()
        +password_hashing()
    }

    class SSEManager {
        +register()
        +unregister()
        +broadcast(event, data)
    }

    FastAPIApp --> MainRouter
    FastAPIApp --> SecretPhotographerRouter
    FastAPIApp --> AdminRouter
    FastAPIApp --> AuthRouter
    FastAPIApp --> SSERouter

    MainRouter --> PhotoService
    SecretPhotographerRouter --> PhotoService
    AdminRouter --> PhotoService
    AuthRouter --> AuthService

    MainRouter --> SSEManager
    SecretPhotographerRouter --> SSEManager
    AdminRouter --> SSEManager
```

### Eventos SSE emitidos por el backend

| Evento | Emisor | Payload |
|---|---|---|
| `new_photo` | `POST /api/gallery/upload` | `{ photo_id }` |
| `gallery_photo_deleted` | `DELETE /api/admin/gallery/{id}` | `{ photo_id }` |
| `new_challenge_photo` | `POST /api/secret-photographer/upload` | `{ photo_id, challenge_id, table_id }` |
| `challenge_photo_deleted` | `DELETE /api/admin/challenges/{cid}/photos/{pid}` | `{ photo_id, challenge_id }` |
| `carousel_updated` | Admin carrusel (upload/delete/reorder) | `{}` |
| `info_updated` | `PUT /api/admin/wedding-info` | `{ novios, fecha, colores, ... }` |
| `winner_selected` | Admin seleccionar/quitar ganador | `{ table_id }` o `{ table_id: null }` |

> El dashboard público abre su propio `EventSource` a `/api/events` (endpoint sin auth) para `new_challenge_photo`, `challenge_photo_deleted` y `winner_selected`.

---

## Árbol de rutas y componentes del Frontend

```mermaid
graph TB
    APP[App]
    NAVBAR[Navbar]
    MAIN[MainPage /]
    SECRET_DASH[SecretDashboardPage /fotografo-secreto]
    FS_PAGE[FotografoSecretoPage /fotografo-secreto/:qr_code]
    ADMIN_PAGE[AdminPage /admin]

    PUB_LIGHTBOX[PhotoLightbox]

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
        TAB_GALERIA[Galeria]
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
    ADMIN_PAGE --> TAB_WINNER

    TAB_RETOS --> CHAL_MODAL
    CHAL_MODAL --> PUB_LIGHTBOX
```

---

## Directorios de fotos

```
Fotos/
├── Carrucel/          # Carrusel de los novios
├── Galeria/           # Fotos subidas por invitados
└── Fotografo-Secreto/
    ├── Mesa-01/       # Fotos de mesa 1 (QR.png + fotos de retos)
    ├── Mesa-02/       # Fotos de mesa 2
    └── ...

Miniaturas/
├── Carrucel/
├── Galeria/
└── Fotografo-Secreto/
    └── Mesa-XX/
```

---

## API (resumen de endpoints)

| Método | Ruta | Auth | Uso |
|---|---|---|---|
| GET | `/api/wedding-info` | No | Info boda + ganador |
| GET | `/api/carousel` | No | Fotos de carrusel |
| GET | `/api/gallery` | No | Galería (paginación offset/limit) |
| POST | `/api/gallery/upload` | No (rate limit) | Subir foto + mensaje |
| GET | `/api/gallery/{id}/download` | No | Descargar una foto |
| POST | `/api/gallery/batch-download` | No | Descargar varias |
| GET | `/api/guest`, `/api/guest/me` | No | Alta/consulta de invitado anónimo |
| GET | `/api/google`, `/api/google/callback` | No | OAuth Google |
| POST | `/api/admin/login`, `/api/logout` | — | Sesión admin |
| GET | `/api/events` | No | SSE |
| GET | `/api/secret-photographer/dashboard` | No | Tablero público en vivo |
| GET | `/api/secret-photographer/table/{qr}` | No | Mesa + retos + my_photo |
| POST | `/api/secret-photographer/upload` | No (rate limit) | Subir foto de reto + mensaje |
| GET | `/api/secret-photographer/challenge/{id}` | No | Detalle reto (blocked) |
| GET | `/api/admin/tables`, `POST/PUT/DELETE` | Admin | Gestión mesas |
| GET | `/api/admin/tables/{id}/photos` | Admin | Fotos por mesa (vista ganador) |
| GET | `/api/admin/tables/{id}/qr` | Admin | Descargar QR |
| GET/POST/PUT/DELETE | `/api/admin/challenges` | Admin | Gestión retos |
| GET | `/api/admin/challenges/{id}/photos` | Admin | Fotos de un reto |
| DELETE | `/api/admin/challenges/{id}/photos/{pid}` | Admin | Borrar foto de reto |
| POST/DELETE | `/api/admin/select-winner` | Admin | Elegir/quitar ganador |
| GET/POST/DELETE | `/api/admin/carousel`, `/gallery` | Admin | Gestión carrusel/galería |
| PUT | `/api/admin/wedding-info` | Admin | Editar info boda/colores |

---

## Reglas de negocio clave

- Los invitados **no necesitan login** — se identifican por UUID en localStorage
- El **UUID lo genera el servidor** (`uuid4` aleatorio), se guarda en DB y se devuelve al cliente
- Google OAuth permite **recuperar identidad** entre dispositivos; al vincularse, el alias se reemplaza por el nombre de Google y se muestra su foto de perfil
- Solo imágenes (validación por **MIME type real** inspeccionando bytes + extensión) — **todos los formatos**, máx **25 MB**
- Nombres de archivo con **UUID** para evitar colisiones
- **Miniatura 150×150px** manteniendo aspect ratio
- **Paginación infinita** con offset/limit
- **15 subidas/minuto** por usuario (rate limit) — también en retos
- Las fotos se sirven **a través de FastAPI** (sin autenticación para visualizar)
- Mensaje opcional (150 caracteres) en galería **y** en fotos de retos
- Fotógrafo Secreto: **1 foto/usuario/reto** (UniqueConstraint `challenge_id+user_id`), máx = nº participantes de la mesa
- Un usuario se asigna a una **mesa una sola vez** (campo `table_id` en User)
- Los retos se bloquean al alcanzar el nº de participantes; admin puede desbloquear para editar/eliminar
- Cada participante ve **solo su propia foto** por reto; los espectadores ven **todas** en el dashboard público
- Dashboard público **en vivo sin login** (EventSource propio); confetti + resaltado al elegir ganador
- Admin puede **seleccionar y deseleccionar** el ganador; se notifica por SSE
- **Admin**: Google OAuth + session cookies + verificación contra emails en `.env`; **admin inicial** desde `.env`
- `Miniaturas/` replica exactamente la estructura de `Fotos/`
- **Limpieza de archivos huérfanos** cada 10s (`ORPHAN_CLEANUP_INTERVAL`)
- **SQLite con WAL mode** para concurrencia; sin backups automáticos

---

## Variables de entorno (`.env`)

El archivo `.env` de la raíz (no versionado) es la **única fuente de secretos**. `.env.example` fue **eliminado del repo** (no se usa en ningún punto del código).

**Carga** (`backend/app/config.py`): `Settings` lee `env_file` desde dos candidatos (los faltantes se ignoran):
1. `backend/.env` — en el contenedor es `/app/.env` (el compose monta `./.env` → `/app/.env`)
2. ruta raíz del repo — hace funcionar los runs locales fuera de Docker

Las variables de entorno reales tienen prioridad sobre los dotenv; `extra="ignore"` tolera claves desconocidas.

| Variable | Uso |
|---|---|
| `ADMIN_EMAIL` | Email del admin (OAuth + login inicial) |
| `ADMIN_PASSWORD` | Password del admin inicial |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `SECRET_KEY` | Clave para session cookies |
| `NOVIO_EMAIL` / `NOVIA_EMAIL` | Presentes en el `.env`, el código actual no las lee |

Opcionales (defaults en `Settings`, no hace falta ponerlas en `.env`): `ORPHAN_CLEANUP_INTERVAL=10`, `FRONTEND_URL=http://localhost:5173`, `MAX_UPLOAD_SIZE=25`, `RATE_LIMIT_PER_MINUTE=15`, `HOST=0.0.0.0`, `PORT=8000`, `DATABASE_URL`, `UPLOAD_DIR=Fotos`, `THUMBNAILS_DIR=Miniaturas`.

---

## Puesta en marcha

- `docker compose up --build` levanta backend y frontend.
- Host: backend publicado en **`localhost:8001`** (→ contenedor `:8000`), frontend en `localhost:5173`.
- `VITE_API_URL=http://localhost:8001` se inyecta como **build-time ARG** (si cambia el puerto, reconstruir con `docker compose build --build-arg VITE_API_URL=...`).
- Para correr el backend local fuera de Docker: `uvicorn app.main:app --reload` desde `backend/` (lee el `.env` raíz).
- Dev frontend: `npm run dev` en `frontend/` (Vite proxya `/api` → `http://localhost:8000`).

---

## Decisiones técnicas adoptadas

| Aspecto | Decisión |
|---|---|
| Gestión de estado | React Context |
| Cliente HTTP | `fetch` nativo + helpers `api()`/`apiUpload()` |
| Paginación | offset/limit |
| Procesamiento de imágenes | Pillow (Python) |
| OAuth | Authlib |
| Generación de QR | `qrcode` (Python) |
| Migraciones BD | `Base.metadata.create_all()` + `ALTER TABLE` manuales en el lifespan (sin Alembic) |
| Config | pydantic-settings |
| Tiempo real | SSE (`new_photo`, `new_challenge_photo`, `challenge_photo_deleted`, `gallery_photo_deleted`, `carousel_updated`, `info_updated`, `winner_selected`) |
| Visualización de fotos | Componente compartido `PhotoLightbox` (lightbox + descarga, opcional eliminar) |
| Entorno dev | `docker compose up --build` |
| Python | Última versión estable |
| Node | Última versión estable |