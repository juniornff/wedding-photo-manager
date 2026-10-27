"""Helpers puros para tests: sin imports de `app` ni side effects de env.

NO importar `conftest` desde los tests: pytest lo registra como módulo
`conftest` y un `from tests.conftest import ...` lo re-importaría como
`tests.conftest`, re-ejecutando el mkdtemp/env y duplicando directorios.
"""

import io

from starlette.datastructures import Headers, UploadFile

IMAGE_EXTS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "GIF": (".gif", "image/gif"),
    "WEBP": (".webp", "image/webp"),
    "BMP": (".bmp", "image/bmp"),
    "TIFF": (".tiff", "image/tiff"),
}


def image_bytes(fmt: str = "JPEG", size=(800, 600), color="red") -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


def make_image_dict(fmt: str = "JPEG", size=(800, 600), color="red") -> dict:
    ext, content_type = IMAGE_EXTS[fmt]
    return {
        "filename": f"test{ext}",
        "content": image_bytes(fmt, size, color),
        "content_type": content_type,
    }


def upload_file(filename: str, content: bytes, content_type: str = "application/octet-stream") -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        size=len(content),
        headers=Headers({"content-type": content_type}),
    )


def make_upload_file(image: dict) -> tuple:
    """Empaqueta un dict de make_image/make_heic como campo `file` de httpx."""
    return ("file", (image["filename"], image["content"], image["content_type"]))
