import asyncio
import json
import uuid
from typing import Any


class SSEManager:
    def __init__(self):
        self._clients: dict[str, asyncio.Queue] = {}

    def register(self) -> tuple[str, asyncio.Queue]:
        client_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._clients[client_id] = queue
        return client_id, queue

    def unregister(self, client_id: str) -> None:
        self._clients.pop(client_id, None)

    async def broadcast(self, event: str, data: Any) -> None:
        message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        dead_clients = []
        for client_id, queue in self._clients.items():
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_clients.append(client_id)
        for client_id in dead_clients:
            self.unregister(client_id)

    @property
    def client_count(self) -> int:
        return len(self._clients)


sse_manager = SSEManager()
