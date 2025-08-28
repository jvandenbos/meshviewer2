import aiosqlite
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
from backend.models import NodeInfo, MeshPacket, TextMessage, NetworkLink, Session, SignalQuality

class Database:
    def __init__(self, db_path: str = "meshtastic.db"):
        self.db_path = db_path
        self.current_session_id: Optional[int] = None
        
    async def initialize(self):
        """Initialize database with schema"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute("PRAGMA journal_mode = WAL")
            
            # Sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at INTEGER NOT NULL,
                    ended_at INTEGER,
                    is_active BOOLEAN DEFAULT TRUE,
                    node_count INTEGER DEFAULT 0,
                    message_count INTEGER DEFAULT 0,
                    UNIQUE(is_active) ON CONFLICT REPLACE
                )
            """)
            
            # Nodes table (current session)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    session_id INTEGER NOT NULL,
                    short_name TEXT NOT NULL,
                    long_name TEXT,
                    hardware_model TEXT,
                    role TEXT DEFAULT 'CLIENT',
                    battery_level INTEGER,
                    voltage REAL,
                    rssi INTEGER,
                    snr REAL,
                    hop_count INTEGER DEFAULT 0,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    last_heard INTEGER NOT NULL,
                    is_online BOOLEAN DEFAULT TRUE,
                    signal_quality TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            # Nodes history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS nodes_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    session_id INTEGER NOT NULL,
                    short_name TEXT NOT NULL,
                    long_name TEXT,
                    hardware_model TEXT,
                    role TEXT,
                    battery_level INTEGER,
                    voltage REAL,
                    rssi INTEGER,
                    snr REAL,
                    hop_count INTEGER,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            # Mesh packets table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mesh_packets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    packet_type TEXT NOT NULL,
                    payload TEXT,
                    rssi INTEGER,
                    snr REAL,
                    hop_count INTEGER DEFAULT 0,
                    channel INTEGER DEFAULT 0,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            # Text messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS text_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    from_id TEXT NOT NULL,
                    from_name TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    to_name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    rssi INTEGER,
                    snr REAL,
                    hop_count INTEGER DEFAULT 0,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            # Network links table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS network_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    rssi INTEGER,
                    snr REAL,
                    success_rate REAL DEFAULT 1.0,
                    last_seen INTEGER NOT NULL,
                    is_direct BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (session_id) REFERENCES sessions (id),
                    UNIQUE(session_id, from_id, to_id)
                )
            """)
            
            # Create indexes for performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_nodes_session ON nodes(session_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_nodes_last_heard ON nodes(last_heard DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_packets_session ON mesh_packets(session_id, timestamp DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON text_messages(session_id, timestamp DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_links_session ON network_links(session_id, last_seen DESC)")
            
            await db.commit()
    
    async def start_session(self) -> int:
        """Start a new session and return its ID"""
        # End any active sessions
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions 
                SET is_active = FALSE, ended_at = ?
                WHERE is_active = TRUE
            """, (int(datetime.now().timestamp()),))
            
            # Create new session
            cursor = await db.execute("""
                INSERT INTO sessions (started_at, is_active)
                VALUES (?, TRUE)
            """, (int(datetime.now().timestamp()),))
            
            self.current_session_id = cursor.lastrowid
            await db.commit()
            
        return self.current_session_id
    
    async def end_session(self):
        """End the current active session"""
        if not self.current_session_id:
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions 
                SET is_active = FALSE, ended_at = ?
                WHERE id = ?
            """, (int(datetime.now().timestamp()), self.current_session_id))
            await db.commit()
            
        self.current_session_id = None
    
    async def get_active_session(self) -> Optional[Session]:
        """Get the current active session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute("""
                SELECT * FROM sessions WHERE is_active = TRUE LIMIT 1
            """)
            row = await cursor.fetchone()
            
            if row:
                return Session(
                    id=row["id"],
                    started_at=datetime.fromtimestamp(row["started_at"]),
                    ended_at=datetime.fromtimestamp(row["ended_at"]) if row["ended_at"] else None,
                    is_active=bool(row["is_active"]),
                    node_count=row["node_count"],
                    message_count=row["message_count"]
                )
        return None
    
    def calculate_signal_quality(self, rssi: Optional[int]) -> SignalQuality:
        """Calculate signal quality from RSSI"""
        if not rssi:
            return None
        if rssi > -75:
            return SignalQuality.EXCELLENT
        elif rssi > -85:
            return SignalQuality.GOOD
        elif rssi > -95:
            return SignalQuality.WEAK
        else:
            return SignalQuality.POOR
    
    async def upsert_node(self, node: NodeInfo):
        """Insert or update node information"""
        if not self.current_session_id:
            await self.start_session()
            
        node.signal_quality = self.calculate_signal_quality(node.rssi)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO nodes (
                    id, session_id, short_name, long_name, hardware_model,
                    role, battery_level, voltage, rssi, snr, hop_count,
                    latitude, longitude, altitude, last_heard, is_online, signal_quality
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node.id, self.current_session_id, node.short_name, node.long_name,
                node.hardware_model, node.role, node.battery_level, node.voltage,
                node.rssi, node.snr, node.hop_count, node.latitude, node.longitude,
                node.altitude, int(node.last_heard.timestamp()), node.is_online,
                node.signal_quality
            ))
            
            # Also save to history
            await db.execute("""
                INSERT INTO nodes_history (
                    node_id, session_id, short_name, long_name, hardware_model,
                    role, battery_level, voltage, rssi, snr, hop_count,
                    latitude, longitude, altitude, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node.id, self.current_session_id, node.short_name, node.long_name,
                node.hardware_model, node.role, node.battery_level, node.voltage,
                node.rssi, node.snr, node.hop_count, node.latitude, node.longitude,
                node.altitude, int(node.last_heard.timestamp())
            ))
            
            await db.commit()
    
    async def get_active_nodes(self, since_seconds: int = 300) -> List[NodeInfo]:
        """Get nodes active in the last N seconds"""
        if not self.current_session_id:
            return []
            
        cutoff = int((datetime.now() - timedelta(seconds=since_seconds)).timestamp())
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute("""
                SELECT * FROM nodes 
                WHERE session_id = ? AND last_heard > ?
                ORDER BY last_heard DESC
            """, (self.current_session_id, cutoff))
            
            rows = await cursor.fetchall()
            nodes = []
            for row in rows:
                nodes.append(NodeInfo(
                    id=row["id"],
                    short_name=row["short_name"],
                    long_name=row["long_name"],
                    hardware_model=row["hardware_model"],
                    role=row["role"],
                    battery_level=row["battery_level"],
                    voltage=row["voltage"],
                    rssi=row["rssi"],
                    snr=row["snr"],
                    hop_count=row["hop_count"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    altitude=row["altitude"],
                    last_heard=datetime.fromtimestamp(row["last_heard"]),
                    is_online=bool(row["is_online"]),
                    signal_quality=row["signal_quality"]
                ))
            
            return nodes
    
    async def save_packet(self, packet: MeshPacket):
        """Save a mesh packet"""
        if not self.current_session_id:
            await self.start_session()
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO mesh_packets (
                    session_id, from_id, to_id, packet_type, payload,
                    rssi, snr, hop_count, channel, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.current_session_id, packet.from_id, packet.to_id,
                packet.packet_type, json.dumps(packet.payload) if packet.payload else None,
                packet.rssi, packet.snr, packet.hop_count, packet.channel,
                int(packet.timestamp.timestamp())
            ))
            await db.commit()
    
    async def save_message(self, message: TextMessage):
        """Save a text message"""
        if not self.current_session_id:
            await self.start_session()
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO text_messages (
                    session_id, from_id, from_name, to_id, to_name,
                    message, rssi, snr, hop_count, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.current_session_id, message.from_id, message.from_name,
                message.to_id, message.to_name, message.message,
                message.rssi, message.snr, message.hop_count,
                int(message.timestamp.timestamp())
            ))
            
            # Update session message count
            await db.execute("""
                UPDATE sessions 
                SET message_count = message_count + 1 
                WHERE id = ?
            """, (self.current_session_id,))
            
            await db.commit()
    
    async def update_network_link(self, link: NetworkLink):
        """Update network link information"""
        if not self.current_session_id:
            await self.start_session()
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO network_links (
                    session_id, from_id, to_id, rssi, snr,
                    success_rate, last_seen, is_direct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.current_session_id, link.from_id, link.to_id,
                link.rssi, link.snr, link.success_rate,
                int(link.last_seen.timestamp()), link.is_direct
            ))
            await db.commit()
    
    async def get_network_topology(self) -> List[NetworkLink]:
        """Get current network topology"""
        if not self.current_session_id:
            return []
            
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute("""
                SELECT * FROM network_links 
                WHERE session_id = ?
                ORDER BY last_seen DESC
            """, (self.current_session_id,))
            
            rows = await cursor.fetchall()
            links = []
            for row in rows:
                links.append(NetworkLink(
                    from_id=row["from_id"],
                    to_id=row["to_id"],
                    rssi=row["rssi"],
                    snr=row["snr"],
                    success_rate=row["success_rate"],
                    last_seen=datetime.fromtimestamp(row["last_seen"]),
                    is_direct=bool(row["is_direct"])
                ))
            
            return links
    
    async def get_recent_messages(self, limit: int = 50) -> List[TextMessage]:
        """Get recent text messages"""
        if not self.current_session_id:
            return []
            
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute("""
                SELECT * FROM text_messages 
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (self.current_session_id, limit))
            
            rows = await cursor.fetchall()
            messages = []
            for row in rows:
                messages.append(TextMessage(
                    from_id=row["from_id"],
                    from_name=row["from_name"],
                    to_id=row["to_id"],
                    to_name=row["to_name"],
                    message=row["message"],
                    rssi=row["rssi"],
                    snr=row["snr"],
                    hop_count=row["hop_count"],
                    timestamp=datetime.fromtimestamp(row["timestamp"])
                ))
            
            return messages[::-1]  # Reverse to get chronological order