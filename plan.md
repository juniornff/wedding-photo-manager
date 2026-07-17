# Proyecto

Gestor de fotos para bodas.

# Descripcion

Aplicación web para poder subir/visualizar/descargar las fotos tomadas por los invitados a una boda. Ademas de contener el modulo para la actividad de "Fotógrafo Secreto"

# Modulos principales de la aplicación

- Principal (subida/vizualizacion/descarga de fotos)
- Fotógrafo Secreto (fotos basadas en retos)
- Administración (Para los novios)

---

# Componentes técnicos

- Backend: FastAPI (Python), SQLAlchemy (async), SQLite
- Frontend: React + Vite + TailwindCSS
- Comunicación en tiempo real: Server‑Sent Events (SSE)
- Almacenamiento: Local (carpeta "Fotos/" con las fotos originales y "Miniaturas/" con miniaturas de las mismas)
- Control de versiones: Git
- Despliegue: Docker Compose

# Reglas de negocio

## Con respecto a los usuarios
- Los usuarios/invitados no necesitan iniciar sesion para subir fotos
- Al ingresar por primera vez al app, se le pide un nombre/alias, en el almacenamiento local del navegador se almacena dicho nombre y un identificador unico, asi como en la base de datos 
- Si la persona quiere ingresar desde otro dispositivo conversando su datos, debe registrarse/iniciar sesion con google (usando google oauth)

## Con respecto a subir fotos
- Validación: Solo se aceptan imágenes (se puede validar extensión y tipo MIME).
- La generación de miniaturas se realiza en el momento de la subida.
- Los archivos se guardan con nombres únicos (UUID) para evitar colisiones.

## Con respecto a la visualización
- Paginación: Carga infinita con offset/limit.

## Seguridad
- Las credenciales e información sensible se almacenan en el archivo .env

---

# Modulo Principal

## Descripción

En esta pantalla se puede visualizar las información basica de la boda (Nombre de los novios, fecha de la boda, carucel de fotos de los novios, etc) ademas de poder subir fotos junto a un pequeño mensaje (150 caracteres)

- Las fotos del carucel de los novios son fotos subidas por los mismos novios y se almacenan en una subcarpeta "Fotos/Carrucel/"
- Las fotos subidas por los participantes se almacenan en la subcarpeta "Fotos/Galeria/"

## Estructura

- Informacion básica de la boda
- Galería de todas las imagenes subidas
- Boton flotante para la subida de tofos

---

# Modulo Fotógrafo Secreto

## Objetivo

Crear modulo para que los invitados participen en un juego por mesas durante la boda.

Cada mesa tendrá:

- Un QR exclusivo.
- Una lista única de 10 retos.
- Los participantes podrán subir fotografías para cada reto.

Al finalizar el evento, los novios visualizarán todas las fotografías y elegirán la mesa ganadora mediante un botón en el panel administrativo.

Las fotos subidas se almacenan en la subcarpeta "Fotos/Fotografo-Secreto/Mesa-XX/" donde cada mesa tiene su carpeta dedicada

## Reglas

- Existen X cantidad de mesas.
- Cada mesa tiene XX retos.
- Cada mesa posee un enlace/QR diferente asociado.
- Al ingresar al enlace/QR de cada mesa los participante se les asocia a dicha mesa.
- Un participante solo puede subir UNA foto por cada reto.
- El maximo de fotografías de cada reto será el numero de participantes de la mesa, luego queda bloqueado. (5 participantes = 5 fotos, 8 participantes = 8 fotos)
- Las fotografías únicamente pertenecen a la mesa desde donde se escaneó el QR.
- Al finalizar, los novios seleccionan manualmente la mesa ganadora.

---

# Modulo administración

## Descripción

Panel donde los novios pueden:
- Administrar las fotos para el carrucel del modulo principal
- Modificar las informaciones presentadas en el modulo principal
- Modificar el esquema de colores de la aplicacion.
- Administrar las fotos subidas a la galeria de fotos.
- Administrar las mesas y los retos (y asociarlos a una mesa) para el modulo de fotografo secreto
- Elegir el ganador del modulo de fotografo secreto