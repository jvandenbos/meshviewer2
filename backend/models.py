from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class NodeRole(str, Enum):
    CLIENT = "CLIENT"
    ROUTER = "ROUTER"
    REPEATER = "REPEATER"
    CLIENT_MUTE = "CLIENT_MUTE"
    ROUTER_CLIENT = "ROUTER_CLIENT"
    TRACKER = "TRACKER"  # New role type

class SignalQuality(str, Enum):
    EXCELLENT = "excellent"  # >-75dBm
    GOOD = "good"           # -75 to -85dBm
    WEAK = "weak"           # -85 to -95dBm
    POOR = "poor"           # <-95dBm

class NodeInfo(BaseModel):
    id: str
    short_name: str
    long_name: Optional[str] = None
    hardware_model: Optional[str] = None
    role: Optional[NodeRole] = NodeRole.CLIENT
    battery_level: Optional[int] = None
    voltage: Optional[float] = None
    rssi: Optional[int] = None
    snr: Optional[float] = None
    hop_count: int = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    last_heard: datetime
    is_online: bool = True
    signal_quality: Optional[SignalQuality] = None

class MeshPacket(BaseModel):
    from_id: str
    to_id: str
    packet_type: str
    payload: Optional[Dict[str, Any]] = None
    rssi: Optional[int] = None
    snr: Optional[float] = None
    hop_count: int = 0
    channel: int = 0
    timestamp: datetime

class TextMessage(BaseModel):
    from_id: str
    from_name: str
    to_id: str
    to_name: str
    message: str
    timestamp: datetime
    rssi: Optional[int] = None
    snr: Optional[float] = None
    hop_count: int = 0

class NetworkLink(BaseModel):
    from_id: str
    to_id: str
    rssi: Optional[int] = None
    snr: Optional[float] = None
    success_rate: float = 1.0
    last_seen: datetime
    is_direct: bool = True

class Session(BaseModel):
    id: Optional[int] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_active: bool = True
    node_count: int = 0
    message_count: int = 0

class WebSocketMessage(BaseModel):
    type: str  # "node_update", "message", "topology_update", "session_event"
    data: Dict[str, Any]
    timestamp: datetime