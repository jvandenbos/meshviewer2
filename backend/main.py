from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any, Optional
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from backend.database import Database
from backend.meshtastic_connector import MeshtasticConnector
from backend.models import (
    NodeInfo, MeshPacket, TextMessage, NetworkLink, 
    Session, WebSocketMessage
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Meshtastic Visualizer", version="1.0.0")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class AppState:
    def __init__(self):
        self.db: Optional[Database] = None
        self.meshtastic: Optional[MeshtasticConnector] = None
        self.websocket_clients: List[WebSocket] = []
        self.current_session: Optional[Session] = None
        self.live_nodes: Dict[str, NodeInfo] = {}
        self.live_messages: List[TextMessage] = []
        self.network_links: Dict[str, NetworkLink] = {}

state = AppState()

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    # Initialize database
    state.db = Database()
    await state.db.initialize()
    
    # Start new session
    session_id = await state.db.start_session()
    state.current_session = await state.db.get_active_session()
    logger.info(f"Started new session: {session_id}")
    
    # Initialize Meshtastic connector
    state.meshtastic = MeshtasticConnector(on_data_callback=process_meshtastic_data)
    
    # Auto-connect to device (will try to find RAK 4631)
    if state.meshtastic.connect():
        logger.info("Connected to Meshtastic device")
    else:
        logger.warning("Failed to auto-connect to Meshtastic device")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if state.meshtastic:
        state.meshtastic.disconnect()
    
    if state.db:
        await state.db.end_session()

async def process_meshtastic_data(data: Dict[str, Any]):
    """Process data from Meshtastic device and update all connected clients"""
    try:
        logger.info(f"📥 Backend processing: {data['type']} for {data.get('node_id', data.get('node', {}).get('id', 'unknown'))}")
        
        # Process based on data type
        if data["type"] == "node_info":
            await handle_node_info(data)
        elif data["type"] == "text_message":
            await handle_text_message(data)
        elif data["type"] == "position_update":
            await handle_position_update(data)
        elif data["type"] == "telemetry":
            await handle_telemetry(data)
        elif data["type"] == "network_link":
            await handle_network_link(data)
        elif data["type"] == "mesh_packet":
            await handle_mesh_packet(data)
        
        # Broadcast to all WebSocket clients
        # Clean data for JSON serialization
        clean_data = json.loads(json.dumps(data, default=str))
        message = WebSocketMessage(
            type=data["type"],
            data=clean_data,
            timestamp=datetime.now()
        )
        logger.info(f"   📡 Broadcasting {data['type']} to {len(state.websocket_clients)} WebSocket clients")
        await broadcast_to_clients(message.dict())
        
    except Exception as e:
        logger.error(f"Error processing Meshtastic data: {e}")

async def handle_node_info(data: Dict):
    """Handle node information update"""
    node_data = data["node"]
    logger.info(f"   Processing node_info: {node_data['id'][:8]} = {node_data.get('short_name', 'Unknown')}")
    
    # Calculate signal quality based on RSSI
    rssi = data.get("rssi")
    signal_quality = None
    if rssi:
        if rssi > -75:
            signal_quality = "excellent"
        elif rssi > -85:
            signal_quality = "good"
        elif rssi > -95:
            signal_quality = "weak"
        else:
            signal_quality = "poor"
    
    node = NodeInfo(
        id=node_data["id"],
        short_name=node_data.get("short_name", f"Node-{node_data['id']}"),
        long_name=node_data.get("long_name"),
        hardware_model=node_data.get("hardware_model"),
        role=node_data.get("role", "CLIENT"),
        battery_level=node_data.get("battery_level"),
        voltage=node_data.get("voltage"),
        rssi=rssi,
        snr=data.get("snr"),
        hop_count=data.get("hop_count", 0),
        signal_quality=signal_quality,
        last_heard=data["timestamp"]
    )
    
    # Update live state
    state.live_nodes[node.id] = node
    logger.info(f"   ✅ Added to live_nodes: {node.id[:8]}, total nodes: {len(state.live_nodes)}")
    
    # Save to database
    await state.db.upsert_node(node)

async def handle_text_message(data: Dict):
    """Handle text message"""
    message = TextMessage(
        from_id=data["from_id"],
        from_name=data["from_name"],
        to_id=data["to_id"],
        to_name=data["to_name"],
        message=data["message"],
        timestamp=data["timestamp"],
        rssi=data.get("rssi"),
        snr=data.get("snr"),
        hop_count=data.get("hop_count", 0)
    )
    
    # Update live state (keep last 100 messages)
    state.live_messages.append(message)
    if len(state.live_messages) > 100:
        state.live_messages = state.live_messages[-100:]
    
    # Save to database
    await state.db.save_message(message)

async def handle_position_update(data: Dict):
    """Handle position update"""
    node_id = data["node_id"]
    logger.info(f"   Processing position: {node_id[:8]} lat={data.get('latitude')}, lon={data.get('longitude')}")
    
    # Update node position if it exists
    if node_id in state.live_nodes:
        state.live_nodes[node_id].latitude = data.get("latitude")
        state.live_nodes[node_id].longitude = data.get("longitude")
        state.live_nodes[node_id].altitude = data.get("altitude")
        state.live_nodes[node_id].last_heard = data["timestamp"]
        logger.info(f"   ✅ Updated position for existing node: {node_id[:8]}")
        
        await state.db.upsert_node(state.live_nodes[node_id])
    else:
        logger.info(f"   ⚠️ Position update for unknown node: {node_id[:8]} - ignoring")

async def handle_telemetry(data: Dict):
    """Handle telemetry update"""
    node_id = data["node_id"]
    device_metrics = data.get("device_metrics", {})
    logger.info(f"   Processing telemetry: {node_id[:8]} battery={device_metrics.get('batteryLevel')}%")
    
    # Update node telemetry if it exists
    if node_id in state.live_nodes:
        node = state.live_nodes[node_id]
        node.battery_level = device_metrics.get("batteryLevel")
        node.voltage = device_metrics.get("voltage")
        node.last_heard = data["timestamp"]
        
        # Update hop count and signal info if available
        if data.get("hop_count") is not None:
            node.hop_count = data.get("hop_count")
        if data.get("rssi") is not None:
            node.rssi = data.get("rssi")
            # Recalculate signal quality
            if node.rssi > -75:
                node.signal_quality = "excellent"
            elif node.rssi > -85:
                node.signal_quality = "good"
            elif node.rssi > -95:
                node.signal_quality = "weak"
            else:
                node.signal_quality = "poor"
        if data.get("snr") is not None:
            node.snr = data.get("snr")
            
        logger.info(f"   ✅ Updated existing node: {node_id[:8]}")
        
        await state.db.upsert_node(node)
    else:
        # Create minimal node entry with hop count and signal info
        logger.info(f"   ⚠️ Creating new node from telemetry: {node_id[:8]}")
        
        # Calculate signal quality based on RSSI
        rssi = data.get("rssi")
        signal_quality = None
        if rssi:
            if rssi > -75:
                signal_quality = "excellent"
            elif rssi > -85:
                signal_quality = "good"
            elif rssi > -95:
                signal_quality = "weak"
            else:
                signal_quality = "poor"
        
        node = NodeInfo(
            id=node_id,
            short_name=f"Node-{node_id[:8]}",
            battery_level=device_metrics.get("batteryLevel"),
            voltage=device_metrics.get("voltage"),
            rssi=rssi,
            snr=data.get("snr"),
            hop_count=data.get("hop_count", 999),  # Use 999 for unknown
            signal_quality=signal_quality,
            last_heard=data["timestamp"]
        )
        state.live_nodes[node_id] = node
        logger.info(f"   ✅ Added to live_nodes: {node_id[:8]}, total nodes: {len(state.live_nodes)}")
        await state.db.upsert_node(node)

async def handle_network_link(data: Dict):
    """Handle network link update"""
    link = NetworkLink(
        from_id=data["from_id"],
        to_id=data["to_id"],
        rssi=data.get("rssi"),
        snr=data.get("snr"),
        last_seen=data["timestamp"],
        is_direct=data.get("is_direct", True)
    )
    
    # Update live state
    link_key = f"{link.from_id}-{link.to_id}"
    state.network_links[link_key] = link
    
    # Save to database
    await state.db.update_network_link(link)

async def handle_mesh_packet(data: Dict):
    """Handle generic mesh packet"""
    packet = MeshPacket(
        from_id=data["from_id"],
        to_id=data["to_id"],
        packet_type=data["packet_type"],
        payload=data.get("payload"),
        rssi=data.get("rssi"),
        snr=data.get("snr"),
        hop_count=data.get("hop_count", 0),
        channel=data.get("channel", 0),
        timestamp=data["timestamp"]
    )
    
    await state.db.save_packet(packet)

async def broadcast_to_clients(message: Dict):
    """Broadcast message to all connected WebSocket clients"""
    if not state.websocket_clients:
        return
    
    disconnected_clients = []
    try:
        # Convert any Pydantic models to dicts
        if hasattr(message.get('data'), 'dict'):
            message['data'] = message['data'].dict()
        message_str = json.dumps(message, default=str)
    except Exception as e:
        logger.error(f"Error serializing message: {e}")
        return
    
    for client in state.websocket_clients:
        try:
            await client.send_text(message_str)
        except:
            disconnected_clients.append(client)
    
    # Remove disconnected clients
    for client in disconnected_clients:
        state.websocket_clients.remove(client)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time updates"""
    await websocket.accept()
    state.websocket_clients.append(websocket)
    
    try:
        # Send initial state to new client
        logger.info(f"📱 New WebSocket client connected. Sending initial state with {len(state.live_nodes)} nodes")
        initial_data = {
            "type": "initial_state",
            "data": {
                "session": state.current_session.dict() if state.current_session else None,
                "nodes": [node.dict() for node in state.live_nodes.values()],
                "messages": [msg.dict() for msg in state.live_messages[-50:]],  # Last 50 messages
                "links": [link.dict() for link in state.network_links.values()]
            },
            "timestamp": datetime.now()
        }
        logger.info(f"   Nodes in initial state: {[node.id[:8] for node in state.live_nodes.values()]}")
        await websocket.send_text(json.dumps(initial_data, default=str))
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle client commands
            if message.get("type") == "send_text":
                text = message.get("text", "")
                destination = message.get("destination")
                if state.meshtastic:
                    state.meshtastic.send_text(text, destination)
                    
            elif message.get("type") == "request_telemetry":
                node_id = message.get("node_id")
                if state.meshtastic:
                    state.meshtastic.request_telemetry(node_id)
                    
            elif message.get("type") == "request_position":
                node_id = message.get("node_id")
                if state.meshtastic:
                    state.meshtastic.request_position(node_id)
                    
    except WebSocketDisconnect:
        if websocket in state.websocket_clients:
            state.websocket_clients.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in state.websocket_clients:
            state.websocket_clients.remove(websocket)

# REST API endpoints
@app.get("/api/session/current")
async def get_current_session():
    """Get current session information"""
    if not state.current_session:
        raise HTTPException(status_code=404, detail="No active session")
    return state.current_session

@app.post("/api/session/new")
async def start_new_session():
    """Start a new session"""
    # End current session
    if state.db:
        await state.db.end_session()
    
    # Clear live state
    state.live_nodes.clear()
    state.live_messages.clear()
    state.network_links.clear()
    
    # Start new session
    session_id = await state.db.start_session()
    state.current_session = await state.db.get_active_session()
    
    # Notify all clients
    await broadcast_to_clients({
        "type": "session_reset",
        "data": {"session": state.current_session.dict()},
        "timestamp": datetime.now()
    })
    
    return state.current_session

@app.get("/api/nodes")
async def get_nodes(active_only: bool = True, since_seconds: int = 300):
    """Get nodes from current session"""
    logger.info(f"📊 API request for nodes. Live nodes in memory: {len(state.live_nodes)}")
    if active_only:
        nodes = await state.db.get_active_nodes(since_seconds)
    else:
        nodes = list(state.live_nodes.values())
    return nodes

@app.get("/api/messages")
async def get_messages(limit: int = 50):
    """Get recent messages"""
    messages = await state.db.get_recent_messages(limit)
    return messages

@app.get("/api/topology")
async def get_topology():
    """Get network topology"""
    links = await state.db.get_network_topology()
    return links

@app.post("/api/device/connect")
async def connect_device(device_path: Optional[str] = None):
    """Connect to Meshtastic device"""
    if not state.meshtastic:
        state.meshtastic = MeshtasticConnector(on_data_callback=process_meshtastic_data)
    
    if state.meshtastic.connect(device_path):
        return {"status": "connected", "device": device_path or "auto-detected"}
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to device")

@app.post("/api/device/disconnect")
async def disconnect_device():
    """Disconnect from Meshtastic device"""
    if state.meshtastic:
        state.meshtastic.disconnect()
        return {"status": "disconnected"}
    return {"status": "not_connected"}

@app.get("/api/device/status")
async def get_device_status():
    """Get device connection status"""
    return {
        "connected": state.meshtastic.connected if state.meshtastic else False,
        "local_node_id": state.meshtastic.local_node_id if state.meshtastic else None
    }

# Serve static files (for production)
# Uncomment when frontend build is ready
# app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)