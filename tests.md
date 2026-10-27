# Tests — Suite automatizada de Wedding Photo Manager

## Qué son y para qué sirven

Son verificaciones automáticas del comportamiento del proyecto: si alguien cambia código y algo se rompe, los tests fallan antes de llegar a producción. Cubren las **reglas de negocio** (subida de fotos, retos del Fotógrafo Secreto, roles de admin, Drive, etc.), no solo que el código "no truene".

La suite tiene dos mitades, cada una con su herramienta:

| Mitad | Herramienta | Qué prueba | Cantidad |
|---|---|---|---|
| Backend (`backend/tests/`) | **pytest** (+ pytest-asyncio, respx) | Servicios, endpoints, migraciones | **173** |
| Frontend (`frontend/src/`) | **Vitest** (+ Testing Library, jsdom) | Utilidades, hooks, componentes | **77** |

**Total: 250 tests.** No requieren `.env` ni levantar el stack (ver [Cómo funcionan](#cómo-funcionan)).

---

## Cómo ejecutarlos

### Backend — 173 tests

```bash
cd backend
.venv/bin/python -m pytest -q          # suite completa (~2m30)
```

Variantes útiles:

```bash
.venv/bin/python -m pytest -q -x                        # corta en el primer fallo
.venv/bin/python -m pytest -q --lf                      # re-ejecuta solo los que fallaron
.venv/bin/python -m pytest tests/test_drive.py -q       # un archivo
.venv/bin/python -m pytest tests/test_admin_api.py::test_select_winner -q   # un test
.venv/bin/python -m pytest -k "upload" -q               # tests cuyo nombre contiene "upload"
.venv/bin/python -m pytest -q -W error::DeprecationWarning   # convierte warnings en errores
```

> Sin el venv del repo, usa el Python del sistema: `python -m pytest -q` (requiere `pip install -r requirements-dev.txt`).

### Frontend — 77 tests

```bash
cd frontend
npm test            # vitest run: una corrida y sale
npx vitest          # modo watch: re-ejecuta al guardar archivos
```

Variantes útiles:

```bash
npm test -- src/components/DownloadDialog.test.jsx   # un archivo
npm test -- -t "ZIP"                                 # tests cuyo nombre contiene "ZIP"
npm run lint                                          # solo lint (oxlint)
npm run build                                         # build de producción
```

### Todo de una vez

```bash
(cd backend && .venv/bin/python -m pytest -q) && \
(cd frontend && npm test && npm run lint)
```

---

## Cómo funcionan

### Backend: aislamiento total del entorno real

La suite **nunca toca** `data/wedding.db`, `Fotos/`, `Miniaturas/` ni el `.env` real. El mecanismo está en `backend/tests/conftest.py`:

1. **Antes de importar cualquier módulo de `app`**, `conftest.py` crea un directorio temporal (`wpm-tests-*`) y fija variables de entorno de prueba:

   ```
   DATABASE_URL  → sqlite en el directorio temporal
   UPLOAD_DIR / THUMBNAILS_DIR → carpetas temporales
   ADMIN_* / NOVIO_* / NOVIA_*  → emails y contraseñas falsas
   ```

   Esto es crítico porque `app.config.settings` y el `engine` de SQLAlchemy son **singletons creados al importar**: si se importara `app` antes de fijar el env, la suite usaría la BD real.

2. **Cada test arranca limpio** con la fixture `db_reset`: recrea el esquema (`drop_all` + `create_all`), siembra los 3 admins (`init_admin`) y la info de boda (`init_wedding_info`), y libera conexiones del engine. Un test no ve los datos de otro.

3. **Fixtures disponibles** (en `conftest.py`): `db` (sesión ORM), `client` (cliente HTTP ASGI sin login), `admin_client` (con sesión de admin), `create_guest`, `make_image`/`make_heic` (imágenes de prueba), `upload_file`, `sse_spy` (espía de eventos SSE), `make_table`/`make_challenge` (fábricas de BD).

4. **Las respuestas HTTP** se prueban con `httpx.AsyncClient(transport=ASGITransport(app))` — sin levantar servidor, todo en memoria.

5. **Servicios externos**: Google Drive se mockea con **respx** (intercepta las llamadas httpx a Google: token, carpetas, subida) y el SSE con el spy `sse_spy`. No hay red real en los tests.

> **Regla de oro:** nunca hacer `from tests.conftest import ...` desde un test — Python lo re-importa como módulo distinto y re-ejecuta la creación del directorio temporal, desincronizando `settings` del env. Lo compartido vive en `tests/helpers.py` (módulo puro, sin efectos secundarios).

### Frontend: Vitest + Testing Library

- **Config** en `vite.config.js` (`test.environment: 'jsdom'`) con setup en `src/test/setup.js`: matchers de jest-dom (`toBeInTheDocument`, `toBeDisabled`…) y `cleanup` automático tras cada test.
- **Ubicación**: los tests viven junto al código (`utils.test.js` al lado de `utils.js`).
- **Estilo**: imports explícitos de `vitest` (`import { describe, it, expect, vi } from 'vitest'`) — sin globals, para que oxlint mantenga el lint limpio.
- **Mocks**: `vi.mock('../api', ...)` para no hacer red, `vi.mock('../context/useAuth', ...)` para simular sesión, `vi.mock('../driveJobs', ...)`. Los datos de sesión mutables se crean con `vi.hoisted`.
- **Temporizadores**: `vi.useFakeTimers()` para el long-press (500 ms) y las descargas con retardo; `userEvent` para clics y subida de archivos reales.
- **Patrón importante**: el modo selección se prueba como lo usa la UI real — `enter()` + `toggle(id)` en el **mismo** `act()` (porque en `PhotoGrid` van juntos en el callback del long-press).

---

## Qué cubre cada archivo

### Backend (`backend/tests/`) — 173

| Archivo | Tests | Cubre |
|---|---:|---|
| `test_admin_api.py` | 34 | Wedding-info PUT+SSE, carrusel CRUD/reorder, tablas+QR, retos CRUD/unlock/fotos, ganador select/clear, usuarios (roles, alias, mesa, borrado anonimiza-o-borra) |
| `test_photo_service.py` | 27 | Validación MIME por magic bytes (6 formatos)+HEIC/HEIF, extensión/tamaño, guardado con UUID, conversión HEIC→JPEG, miniaturas ≤150px, ZIP, rate limit 15/min, limpieza de huérfanos |
| `test_drive.py` | 27 | Rate limit de Drive, refresh token (caché/`invalid_grant`/errores), lote en segundo plano (happy, dedupe, needs_auth, subcarpetas de retos), endpoints status/save-batch/job |
| `test_auth_api.py` | 21 | Registro/consulta de invitado, login admin (ok/malas creds/rol guest), logout, matriz de 12 guards 401 |
| `test_main_api.py` | 20 | Wedding-info, subida a galería (happy/errores/rate limit), paginación, descarga individual y batch ZIP, mounts estáticos, fotos de autor borrado → Anónimo |
| `test_secret_photographer.py` | 19 | Dashboard público, mesa por QR (asignación única, 409 al reasignar), subida de retos (duplicado/tope/mesa distinta/unlock/mensaje 150), `my_photo` solo propio, blocked |
| `test_auth_service.py` | 8 | PBKDF2 roundtrip, hash legacy/malformados, `init_admin`/`init_wedding_info` idempotentes |
| `test_migrations.py` | 7 | `_ensure_user_roles` (columnas+índice+borrado de placeholders), `_ensure_nullable_user_id` (reconstrucción de tablas), lifespan completo sobre esquema viejo |
| `test_sse_manager.py` | 5 | Registro/broadcast/unregister/evicción por cola llena |
| `test_smoke.py` | 5 | Arrepentimiento rápido: wedding-info, `/api/admin/me` 201/401, galería vacía |

### Frontend (`frontend/src/`) — 77

| Archivo | Tests | Cubre |
|---|---:|---|
| `components/DownloadDialog.test.jsx` | 15 | ZIP bloqueado >100, textos de busy, callbacks, backdrop, sección Drive (vinculado/no/autorizar), errores `drive_reconnect`/`drive_not_authorized` |
| `utils.test.js` | 12 | URLs de foto/miniatura, `photoSrc`, `authorName` (Google>alias>Anónimo), descarga ZIP e individuales con timers |
| `api.test.js` | 10 | `credentials: include`, merge de headers, `detail` de error, 204, FormData, blob |
| `hooks/usePhotoSelection.test.js` | 10 | Toggle/selectAll/clear/prune y la regla: sin fotos seleccionadas sale del modo selección |
| `hooks/useLongPress.test.js` | 7 | Dispara a 500 ms, cancela con pointerup o movimiento >10 px, `consumeClick` |
| `components/PhotoUpload.test.jsx` | 9 | Login obligatorio, recorte de mensaje a 150, FormData, errores, cancelar |
| `components/Toaster.test.jsx` | 8 | Evento `app-toast`, duraciones (success 6 s / error 10 s), links, cierre manual |
| `components/SelectionToolbar.test.jsx` | 6 | Pluralización, callbacks, estados disabled con busy |

---

## Integración continua (CI)

`.github/workflows/ci.yml` ejecuta en paralelo, en cada **push** a `master`/`main`/`test/**` y en cada **PR** a `master`/`main`:

| Job | Entorno | Pasos |
|---|---|---|
| `backend` | Ubuntu + Python 3.13 (cache pip) | `pip install -r requirements.txt -r requirements-dev.txt` → `pytest -q` |
| `frontend` | Ubuntu + Node 20 (cache npm) | `npm ci` → `npm run lint` → `npm test` → `npm run build` |

El job de backend no necesita secretos ni `.env`: la suite es autocontenida (ver arriba).

---

## Dependencias de testing

- **Backend** — `backend/requirements-dev.txt`: `pytest`, `pytest-asyncio` (modo auto), `pytest-cov`, `respx` (mock de httpx para Drive).
- **Frontend** — `devDependencies` en `frontend/package.json`: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`. Ojo: se usa **jsdom 26** a propósito — el 30 instala undici 8 que rompe en Node 20 (`zlib.createZstdDecompress`).
