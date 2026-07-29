"""WebSocket router — clients subscribe to a channel stream."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ws.manager import ws_manager
from auth.jwt import decode_token

router = APIRouter()


@router.websocket("/channel/{channel_id}")
async def channel_ws(
    websocket: WebSocket,
    channel_id: str,
    token: str = Query(...),
):
    """
    Connect: ws://host/ws/channel/{channel_id}?token=<jwt>
    The client receives all new messages posted to that channel in real-time.
    """
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await ws_manager.connect(websocket, channel_id)
    try:
        while True:
            # Keep-alive: client can send pings; we echo them
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel_id)
