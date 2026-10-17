# Actualizaciones de producción

Guía para actualizar la instancia de **producción** alojada en el home server
(`~/Applications/wedding-photo-manager/`, dominio `boda.nehemiasfeliz.com`).

> En el servidor, el archivo de Compose de producción reemplazó al de desarrollo:
> **`docker-compose.yml` es el de producción** (sin puertos publicados, servicios en
> `default` + la red externa `proxy-net` donde corre Caddy). Todos los comandos de
> esta guía se ejecutan **en el servidor** salvo que se indique "local".

---

## 1. Antes de actualizar: backup (en el servidor)

La BD vive en `data/wedding.db` (más `Fotos/` y `Miniaturas/`). Hacer copia antes
de tocar nada:

```bash
cd ~/Applications/wedding-photo-manager
mkdir -p backups
tar czf "backups/wedding-data-$(date +%Y%m%d-%H%M%S).tar.gz" data
```

*(Opcional pero recomendado en cambios grandes: incluir `Fotos/ Miniaturas/` en el
tar si quieres poder revertir fotos.)*

---

## 2. Copiar el código nuevo (en la máquina local)

Desde la raíz del repo:

```bash
rsync -av --exclude 'data/' --exclude 'Fotos/' --exclude 'Miniaturas/' \
  --exclude 'node_modules/' --exclude '__pycache__/' --exclude 'dist/' \
  --exclude '*.pyc' --exclude '*.db*' --exclude '.git' \
  ./ usuario@servidor:~/Applications/wedding-photo-manager/
```

- **Nunca se copian `data/`, `Fotos/` ni `Miniaturas/`: la instancia de producción
  mantiene su propia base de datos y fotos.**
- `.env` **no se sobreescribe** salvo que lo incluyas explícitamente (rsync lo
  copia por defecto). Para no tocarlo: añade `--exclude '.env'`. Si cambias
  secretos o variables, edítalos a mano en el servidor (sección 3).

---

## 3. Cambios en `.env` (en el servidor, solo si hacen falta)

```bash
cd ~/Applications/wedding-photo-manager
nano .env        # o el editor que prefieras
chmod 600 .env
```

Recuerda que en producción: `FRONTEND_URL=https://boda.nehemiasfeliz.com`,
`CORS_ALLOWED_ORIGINS=` (vacío), `VITE_PROXY_TARGET=http://backend:8000` y la
`SECRET_KEY` propia del servidor.

Tras cambiar `.env` **no hace falta rebuild**, pero sí recrear los contenedores
para que Compose reinyecte las variables. Se hace en la sección siguiente con
`up -d` (sin `--build`).

---

## 4. Aplicar la actualización (en el servidor)

```bash
cd ~/Applications/wedding-photo-manager
docker compose up -d --build     # --build: recompila si cambió el código
docker compose ps
```

- Si **solo** cambió `.env` (o settings de servicios), usa `docker compose up -d`
  para recrear los contenedores sin reconstruir las imágenes.
- Si cambiaron **dependencias** (`requirements.txt` del backend o `package.json`
  del frontend), el `--build` es obligatorio: la imagen instala las deps en build time.
- Las migraciones de esquema (`ALTER TABLE`, creación de tablas) se ejecutan solas
  en el arranque del backend y son **idempotentes**, así que se pueden aplicar
  sobre la BD existente sin pasos manuales.
- Los `container_name` (`wedding-photo-manager-backend` / `-frontend`) están
  fijos: la Caddyfile no cambia y **no hay que recargar Caddy** a menos que se
  modifique el propio `Caddyfile.md`.

---

## 5. Verificar

```bash
docker compose logs backend --tail 50           # sin errores de migración/arranque
curl -k https://boda.nehemiasfeliz.com/api/wedding-info
```

Comprobar en el navegador: portada con fecha/mensaje, login admin, galería,
`/fotografo-secreto` (SSE en vivo) y `/privacidad` + `/terminos`.

---

## 6. Rollback

Si algo falla:

1. `cd ~/Applications/wedding-photo-manager && docker compose logs backend` para
   ver el error.
2. Restaurar el backup de datos si la BD se corrompió:
   ```bash
   tar xzf backups/wedding-data-YYYYMMDD-HHMMSS.tar.gz
   ```
   El backend monta `./data:/app/data`, así que basta con restaurar el directorio
   y reiniciar.
3. Re-desplegar con la versión anterior: copiar de nuevo el código anterior
   (o `git checkout` si el servidor tuviera git) y `docker compose up -d --build`.

---

## Notas

- **SSH + DNS**: el flujo asume que el servidor ya tiene Docker Compose v2, la red
  `proxy-net` con Caddy, el DNS `boda.nehemiasfeliz.com` → servidor (Cloudflare) y
  el OAuth de Google con el redirect URI `https://boda.nehemiasfeliz.com/api/google/callback`.
- Cloudflare en modo proxy bufferear el SSE: el frontend reconecta solo.
- `docker compose` sin `-f`: en el servidor **no debe existir** el compose de dev
  (recién desplegado, el `docker-compose.prod.yml` fue renombrado a
  `docker-compose.yml`). Si reinstalas el repo completo, vuelve a hacer ese rename.