# Caddyfile — producción (boda.nehemiasfeliz.com)
# =================================================
# Este bloque se copia en la Caddyfile del contenedor Caddy del home server.
# Caddy corre en la red Docker externa "proxy-net" (la misma que usa el
# docker-compose.prod.yml de este proyecto).

boda.nehemiasfeliz.com {
	tls /etc/caddy/cloudflare-origin/cert.pem /etc/caddy/cloudflare-origin/key.pem

	# API, imágenes, miniaturas, SSE y OAuth Google caen todos bajo /api/*
	reverse_proxy /api/* wedding-photo-manager-backend-1:8000

	# Frontend (vite dev, que además proxea /api al backend)
	reverse_proxy wedding-photo-manager-frontend-1:5173
}

# Notas:
# - "wedding-photo-manager-backend-1"/"wedding-photo-manager-frontend-1" son los
#   nombres de contenedor del proyecto (compose generó los nombres así con el
#   proyecto por defecto). Verifica con `docker compose -f docker-compose.prod.yml ps`.
# - tls: usa el certificado de origen de Cloudflare (~15 años). La renovación es
#   manual: reemplaza cert.pem/key.pem y recarga Caddy (`docker exec <caddy> caddy reload`).
# - Si cambiara el nombre del proyecto/toleras otro nombre de servicio, ajusta el
#   hostname del reverse_proxy (último paso: nombre-de-contenedor:puerto).
# - Cloudflare en modo proxy (nube naranja): el SSE (/api/events) puede sufrir
#   buffering; el frontend ya reconecta solo el EventSource. Uploads ≤ 25 MB caben
#   en el límite de Cloudflare (100 MB en plan free).