"""WebSocket connection manager for real-time communication."""

import asyncio
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for multiple clients."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.
        
        Args:
            client_id: Unique identifier for the client
            websocket: WebSocket connection
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
        
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection.
        
        Args:
            client_id: Unique identifier for the client
        """
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
        
        logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(
        self,
        message: dict,
        client_id: str
    ) -> bool:
        """Send a message to a specific client.
        
        Args:
            message: Message to send (will be JSON encoded)
            client_id: Target client ID
            
        Returns:
            True if sent successfully, False otherwise
        """
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                await self.disconnect(client_id)
                return False
        return False
    
    async def send_to_agent_console(
        self,
        agent_id: str,
        message: dict
    ) -> None:
        """Send a message to agent's console (all connected clients).
        
        Args:
            agent_id: Agent identifier
            message: Message to send
        """
        message["agent_id"] = agent_id
        message["type"] = message.get("type", "console")
        await self.broadcast(message)
    
    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients.
        
        Args:
            message: Message to broadcast (will be JSON encoded)
        """
        disconnected_clients: List[str] = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
    
    async def send_heartbeat(self, client_id: str) -> bool:
        """Send a heartbeat/ping to a client.
        
        Args:
            client_id: Target client ID
            
        Returns:
            True if sent successfully, False otherwise
        """
        return await self.send_personal_message(
            {"type": "ping", "timestamp": asyncio.get_event_loop().time()},
            client_id
        )
    
    def get_connection_count(self) -> int:
        """Get the number of active connections.
        
        Returns:
            Number of active connections
        """
        return len(self.active_connections)
    
    def is_connected(self, client_id: str) -> bool:
        """Check if a client is connected.
        
        Args:
            client_id: Client ID to check
            
        Returns:
            True if connected, False otherwise
        """
        return client_id in self.active_connections


# Global connection manager instance
connection_manager = ConnectionManager()
