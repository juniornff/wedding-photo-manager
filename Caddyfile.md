# Caddyfile — producción (boda.nehemiasfeliz.com)
# =================================================
# Este bloque se copia en la Caddyfile del contenedor Caddy del home server.
# Caddy corre en la red Docker externa "proxy-net" (la misma que usa el
# docker-compose de producción, desplegado en el servidor como docker-compose.yml).

boda.nehemiasfeliz.com {
	tls /etc/caddy/cloudflare-origin/cert.pem /etc/caddy/cloudflare-origin/key.pem

	# API, imágenes, miniaturas, SSE y OAuth Google caen todos bajo /api/*
	reverse_proxy /api/* wedding-photo-manager-backend:8000

	# Frontend (vite dev, que además proxea /api al backend)
	reverse_proxy wedding-photo-manager-frontend:5173
}

# Notas:
# - "wedding-photo-manager-backend"/"wedding-photo-manager-frontend" son los
#   nombres de contenedor fijados con `container_name` en el compose de
#   producción (en el servidor: docker-compose.yml). Verifica con `docker compose ps`.
# - tls: usa el certificado de origen de Cloudflare (~15 años). La renovación es
#   manual: reemplaza cert.pem/key.pem y recarga Caddy (`docker exec <caddy> caddy reload`).
# - Los nombres de contenedor están fijados (no dependen del nombre del proyecto
#   de Compose); si los cambias, ajusta el hostname del reverse_proxy
#   (patrón: nombre-de-contenedor:puerto).
# - Cloudflare en modo proxy (nube naranja): el SSE (/api/events) puede sufrir
#   buffering; el frontend ya reconecta solo el EventSource. Uploads ≤ 25 MB caben
#   en el límite de Cloudflare (100 MB en plan free).