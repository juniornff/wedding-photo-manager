# AGENTS.md — Wedding Photo Manager

## Project status
Functional. Backend (FastAPI) and Frontend (React) are built and verified. Run via `docker compose up`. `README.md` contains the complete architecture with Mermaid diagrams (ER, use cases, sequences, states, component trees).

## Tech stack
- **Backend**: FastAPI + SQLAlchemy (async) + SQLite (WAL mode)
- **Backend libs**: Pillow (thumbnails), Authlib (OAuth), qrcode (QR gen)
- **Frontend**: React + Vite + TailwindCSS + React Router
- **Frontend HTTP**: fetch nativo + React Context (no axios, no Redux)
- **Real-time**: Server-Sent Events (SSE)
- **Storage**: Local filesystem (`Fotos/`, `Miniaturas/`)
- **Deployment**: Docker Compose (backend + frontend); Caddy aparte
- **Auth**: Google OAuth for cross-device sync; anonymous guests use localStorage UUID
- **Testing**: pytest (backend) + Vitest (frontend)

## Architecture — 3 modules
| Module | Purpose |
|---|---|
| **Main** | Upload/view/download photos; wedding info + carousel + gallery |
| **Fotógrafo Secreto** | Per-table QR challenges; 10 retos/table, 1 photo/participant/reto, max 3 photos/reto |
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
- Reto bloqueado al llegar a 3 fotos; admin puede desbloquear solo para editar/eliminar
- QR generado como PNG estático en `Fotos/Fotografo-Secreto/Mesa-XX/QR.png`
- Admin elige ganador subjetivamente; vista en grilla agrupada por reto

## Database entities (derived from plan)
- **User** — anonymous (uuid + alias) or Google-authenticated; `table_id` asignado una vez; guarda `google_name`, `google_photo`
- **WeddingInfo** — couple names, date, color scheme, `winner_table_id`
- **CarouselPhoto** — carousel images (ordered)
- **GalleryPhoto** — guest uploads in main module
- **Table** — mesas with unique QR links
- **Challenge** — retos linked to a table (10 per table)
- **ChallengePhoto** — per-reto submissions (1/user/reto, max 3/reto)
- **Admin** — wedding couple credentials

## Conventions
- `README.md` is the canonical architecture reference with Mermaid diagrams
- `plan.md` is the original specification
- This file (AGENTS.md) is the quick-start for new agent sessions
