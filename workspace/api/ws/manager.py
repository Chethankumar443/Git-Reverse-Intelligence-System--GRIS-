"""WebSocket connection manager — pub/sub per channel."""
import json
from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    """Tracks open WebSocket connections, keyed by channel_id."""

    def __init__(self):
        # channel_id → set of WebSockets
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, channel_id: str):
        await websocket.accept()
        self._connections[channel_id].add(websocket)

    def disconnect(self, websocket: WebSocket, channel_id: str):
        self._connections[channel_id].discard(websocket)

    async def broadcast(self, channel_id: str, payload: dict):
        """Send payload to all subscribers of a channel."""
        dead = set()
        for ws in self._connections.get(channel_id, set()):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections[channel_id].discard(ws)


ws_manager = ConnectionManager()
