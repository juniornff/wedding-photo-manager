"""Tests unitarios de app.services.sse_manager (broadcast + evicción)."""

import json

from app.services.sse_manager import SSEManager


def _parse(raw: str) -> tuple[str, dict]:
    name, payload = None, None
    for line in raw.splitlines():
        if line.startswith("event: "):
            name = line[7:]
        elif line.startswith("data: "):
            payload = json.loads(line[6:])
    return name, payload


async def test_register_devuelve_id_y_cola_unicos():
    m = SSEManager()
    id1, q1 = m.register()
    id2, q2 = m.register()
    assert id1 != id2
    assert q1 is not q2
    assert len(m._clients) == 2


async def test_broadcast_entrega_a_todos_los_clientes():
    m = SSEManager()
    _, q1 = m.register()
    _, q2 = m.register()

    await m.broadcast("new_photo", {"photo_id": 7})

    assert _parse(q1.get_nowait()) == ("new_photo", {"photo_id": 7})
    assert _parse(q2.get_nowait()) == ("new_photo", {"photo_id": 7})


async def test_unregister_deja_de_recibir():
    m = SSEManager()
    id1, q1 = m.register()
    id2, q2 = m.register()
    m.unregister(id1)

    await m.broadcast("winner_selected", {"table_id": 3})

    assert q1.empty()
    assert _parse(q2.get_nowait()) == ("winner_selected", {"table_id": 3})
    assert len(m._clients) == 1


async def test_unregister_id_inexistente_no_falla():
    m = SSEManager()
    m.unregister("no-existe")


async def test_cola_llena_evicta_cliente():
    m = SSEManager()
    id1, q1 = m.register()
    _, q2 = m.register()

    for _ in range(q1.maxsize):  # llenar hasta el tope (100)
        q1.put_nowait("buffer")

    await m.broadcast("new_photo", {"photo_id": 1})

    assert id1 not in m._clients  # evicto por QueueFull
    assert len(m._clients) == 1
    # el otro cliente sí recibió el evento
    assert _parse(q2.get_nowait()) == ("new_photo", {"photo_id": 1})
