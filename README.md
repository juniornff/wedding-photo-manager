# Wedding Photo Manager

Aplicación web para gestionar fotos de bodas: subida, visualización y descarga por parte de los invitados, más el módulo interactivo **Fotógrafo Secreto**.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | FastAPI + SQLAlchemy (async) + SQLite (WAL mode) |
| Backend libs | Pillow (thumbnails), Authlib (OAuth), qrcode (QR gen) |
| Frontend | React + Vite + TailwindCSS + React Router |
| Frontend HTTP | fetch nativo + React Context (sin Redux/axios) |
| Tiempo real | Server-Sent Events (SSE) |
| Almacenamiento | Local filesystem (`Fotos/`, `Miniaturas/`) |
| Autenticación | Google OAuth + UUID anónimo (localStorage) |
| Despliegue | Docker Compose (backend + frontend); Caddy aparte |
| Testing | pytest (backend) + Vitest (frontend) |

---

## Arquitectura del sistema

```mermaid
graph TB
    subgraph Frontend
        REACT[React + Vite]
        TAILWIND[TailwindCSS]
        SSE[SSE Client]
    end

    subgraph Backend
        FASTAPI[FastAPI]
        SQLA[SQLAlchemy Async]
        SSE_SRV[SSE Endpoint]
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
    FS[Módulo Fotógrafo Secreto<br/>Retos por mesa / QR]
    ADMIN[Módulo Admin<br/>Panel de novios]

    MAIN --> FS
    ADMIN --> MAIN
    ADMIN --> FS
```

### Módulo Principal
- Información de la boda (nombres, fecha)
- Carrusel de fotos de los novios (`Fotos/Carrucel/`)
- Galería de fotos subidas por invitados (`Fotos/Galeria/`)
- Botón flotante para subir fotos + mensaje (150 caracteres)

### Módulo Fotógrafo Secreto
- Cada mesa tiene un QR único (generado como PNG estático en `Fotos/Fotografo-Secreto/Mesa-XX/QR.png`)
- 10 retos por mesa (creados uno por uno desde el panel admin)
- 1 foto por participante por reto, máximo 3 fotos por reto
- El usuario se asigna a una mesa al escanear el QR (una sola vez, error si reasigna)
- Fotos almacenadas en `Fotos/Fotografo-Secreto/Mesa-XX/`
- Admin elige ganador manualmente; visualización en grilla agrupada por reto

### Módulo Admin
- Gestionar carrusel, info de boda, esquema de colores
- Administrar mesas y retos
- Elegir mesa ganadora del Fotógrafo Secreto

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
        string name UK
        string qr_code UK
        datetime created_at
    }

    Challenge {
        int id PK
        int table_id FK
        string description
        int sort_order
        datetime created_at
    }

    ChallengePhoto {
        int id PK
        string uuid UK
        string path
        string thumbnail_path
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

---

## Diagrama de Casos de Uso

```mermaid
graph TB
    INVITADO[Invitado]
    NOVIOS[Novios]
    GOOGLE[Usuario Google OAuth]

    subgraph "Módulo Principal"
        UC1[Ver info boda]
        UC2[Ver carrusel]
        UC3[Subir foto + mensaje]
        UC4[Ver galería]
        UC5[Descargar foto]
    end

    subgraph "Fotógrafo Secreto"
        UC6[Escanear QR mesa]
        UC7[Ver retos de mesa]
        UC8[Subir foto para reto]
    end

    subgraph "Admin"
        UC9[Gestionar carrusel]
        UC10[Editar info boda]
        UC11[Cambiar colores]
        UC12[Administrar mesas]
        UC13[Crear/editar retos]
        UC14[Elegir mesa ganadora]
        UC15[Moderar galería]
    end

    INVITADO --> UC1
    INVITADO --> UC2
    INVITADO --> UC3
    INVITADO --> UC4
    INVITADO --> UC5
    INVITADO --> UC6
    INVITADO --> UC7
    INVITADO --> UC8

    NOVIOS --> UC9
    NOVIOS --> UC10
    NOVIOS --> UC11
    NOVIOS --> UC12
    NOVIOS --> UC13
    NOVIOS --> UC14
    NOVIOS --> UC15

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
    Note over C,API: SSE notifica nueva foto
    API-->>C: SSE: new_photo { photo_id }
```

### Flujo: Fotógrafo Secreto

```mermaid
sequenceDiagram
    participant C as Cliente (Browser)
    participant API as FastAPI
    participant DB as SQLite

    Note over C: Escanea QR de mesa
    C->>API: GET /api/secret-photographer/table/{qr_code}
    API->>DB: SELECT table + challenges
    DB-->>API: table_data + challenges[1..10]
    API-->>C: { table_id, challenges }

    Note over C: Participante elige reto
    C->>API: GET /api/secret-photographer/challenge/{id}
    API->>DB: SELECT challenge_photos (count)
    DB-->>API: photo_count
    alt photo_count >= 3
        API-->>C: { blocked: true, message: "Reto completo" }
    else photo_count < 3
        API-->>C: { challenge, can_upload: true }
    end

    Note over C: Subir foto para reto
    C->>API: POST /api/secret-photographer/upload { challenge_id, file, user_id }
    API->>DB: SELECT count WHERE challenge_id + user_id
    alt Ya subió foto para este reto
        API-->>C: 409 { error: "Ya subiste una foto para este reto" }
    else
        API->>DB: SELECT count WHERE challenge_id
        alt count >= 3
            API-->>C: 409 { error: "Reto completo (3 fotos)" }
        else
            API->>API: Guardar archivo
            API->>DB: INSERT challenge_photo
            DB-->>API: photo_id
            API-->>C: 201 { photo_id }
        end
    end
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

    A->>API: POST /api/admin/select-winner { table_id }
    API->>DB: UPDATE wedding_info SET winner_table_id = table_id
    DB-->>API: success
    API-->>A: { winner: table_name }
    Note over A,API: SSE broadcast winner
    API-->>A: SSE: winner_selected { table_id }
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
    Finalizado --> [*]
```

---

## Diagrama de Componentes del Backend

```mermaid
classDiagram
    class FastAPIApp {
        +mount_routers()
        +configure_middleware()
        +setup_sse()
    }

    class MainRouter {
        +get_wedding_info()
        +list_gallery()
        +upload_photo()
        +download_photo()
    }

    class SecretPhotographerRouter {
        +get_table_by_qr()
        +get_challenge()
        +upload_challenge_photo()
    }

    class AdminRouter {
        +get_dashboard()
        +manage_carousel()
        +update_wedding_info()
        +update_colors()
        +manage_tables()
        +manage_challenges()
        +select_winner()
    }

    class AuthRouter {
        +register_guest()
        +google_login()
        +google_callback()
    }

    class PhotoService {
        +validate_file()
        +save_photo()
        +generate_thumbnail()
        +delete_photo()
    }

    class TableService {
        +create_table()
        +get_challenges()
        +check_upload_limits()
    }

    class SSEManager {
        +broadcast_new_photo()
        +broadcast_winner()
        +manage_connections()
    }

    FastAPIApp --> MainRouter
    FastAPIApp --> SecretPhotographerRouter
    FastAPIApp --> AdminRouter
    FastAPIApp --> AuthRouter

    MainRouter --> PhotoService
    SecretPhotographerRouter --> PhotoService
    SecretPhotographerRouter --> TableService
    AdminRouter --> PhotoService
    AdminRouter --> TableService

    PhotoService --> SSEManager
```

---

## Árbol de componentes del Frontend

```mermaid
graph TB
    APP[App]
    LAYOUT[Layout]
    MAIN[MainPage]
    FS_PAGE[FotografoSecretoPage]
    ADMIN_PAGE[AdminPage]

    subgraph "MainPage"
        WEDDING_INFO[WeddingInfo]
        CAROUSEL[Carousel]
        GALLERY[Gallery]
        UPLOAD_BTN[UploadButton]
    end

    subgraph "FotografoSecretoPage"
        TABLE_VIEW[TableView]
        CHALLENGE_LIST[ChallengeList]
        PHOTO_UPLOAD[PhotoUpload]
        PHOTO_GRID[PhotoGrid]
    end

    subgraph "AdminPage"
        DASHBOARD[Dashboard]
        CAROUSEL_MGR[CarouselManager]
        INFO_EDITOR[InfoEditor]
        COLOR_PICKER[ColorPicker]
        TABLE_MGR[TableManager]
        CHALLENGE_EDITOR[ChallengeEditor]
        WINNER_SELECT[WinnerSelector]
    end

    APP --> LAYOUT
    LAYOUT --> MAIN
    LAYOUT --> FS_PAGE
    LAYOUT --> ADMIN_PAGE
```

---

## Directorios de fotos

```
Fotos/
├── Carrucel/          # Carrusel de los novios
├── Galeria/           # Fotos subidas por invitados
└── Fotografo-Secreto/
    ├── Mesa-01/       # Fotos de mesa 1
    ├── Mesa-02/       # Fotos de mesa 2
    └── ...

Miniaturas/
├── Carrucel/
├── Galeria/
└── Fotografo-Secreto/
    └── Mesa-XX/
```

---

## Reglas de negocio clave

- Los invitados **no necesitan login** — se identifican por UUID en localStorage
- El **UUID lo genera el servidor** (`uuid4` aleatorio), se guarda en DB y se devuelve al cliente
- Google OAuth permite **recuperar identidad** entre dispositivos; al vincularse, el alias se reemplaza por el nombre de Google y se muestra su foto de perfil
- Solo imágenes (validación por **MIME type real** inspeccionando bytes + extensión)
- **Todos los formatos** de imagen son aceptados
- Tamaño máximo: **25 MB**
- Nombres de archivo con **UUID** para evitar colisiones
- **Miniatura 150×150px** generada automáticamente en la subida (manteniendo aspect ratio)
- **Paginación infinita** con offset/limit
- **15 subidas/minuto** por usuario (rate limit)
- Las fotos se sirven **a través de FastAPI** (sin autenticación para visualizar)
- Fotógrafo Secreto: **1 foto/usuario/reto**, máximo **3 fotos/reto**
- Un usuario se asigna a una **mesa una sola vez** (campo `table_id` en User)
- Los retos bloqueados al llegar a 3 fotos; admin puede desbloquear solo para editar/eliminar
- **Admin**: Google OAuth + session cookies + verificación contra emails en `.env`
- **Admin inicial** creado desde `.env` (email + password)
- `Miniaturas/` replica exactamente la estructura de `Fotos/`
- **Limpieza de archivos huérfanos** cada 10s (configurable vía `.env`)
- **SQLite con WAL mode** para concurrencia
- Sin backups automáticos (evento pequeño: ~50 invitados)
- Configuración sensible en **`.env`** (no versionado)

## Variables de entorno (`.env`)

| Variable | Descripción |
|---|---|
| `ADMIN_EMAIL` | Email del admin para OAuth |
| `ADMIN_PASSWORD` | Password del admin inicial |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `SECRET_KEY` | Clave para session cookies |
| `ORPHAN_CLEANUP_INTERVAL` | Intervalo de limpieza de huérfanos (default: 10) |

## Decisiones técnicas adoptadas

| Aspecto | Decisión |
|---|---|
| Gestión de estado | React Context |
| Cliente HTTP | `fetch` nativo + hook personalizado |
| Paginación | offset/limit |
| Procesamiento de imágenes | Pillow (Python) |
| OAuth | Authlib |
| Generación de QR | `qrcode` (Python) |
| Migraciones BD | `SQLAlchemy.create_all()` al iniciar |
| Entorno dev | `docker compose up` |
| Python | Última versión estable |
| Node | Última versión estable |
