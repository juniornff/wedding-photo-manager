import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.sse_manager import sse_manager

sse_router = APIRouter(tags=["sse"])


@sse_router.get("/api/events")
async def sse_endpoint():
    client_id, queue = sse_manager.register()

    async def event_generator():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.unregister(client_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
