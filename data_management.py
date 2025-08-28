#!/usr/bin/env python3
"""
Meshtastic Network Visualizer - Data Management
Database operations for inserting, updating, and querying Meshtastic network data.
"""

import sqlite3
import json
import time
import hashlib
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from contextlib import contextmanager

@dataclass
class NodeInfo:
    """Represents a Meshtastic node."""
    id: int
    short_name: str = ""
    long_name: str = ""
    is_licensed: bool = False
    hardware_model_id: int = 0
    role_id: int = 0
    macaddr: str = ""
    
@dataclass  
class Position:
    """GPS position data."""
    latitude_i: int
    longitude_i: int
    altitude: int = 0
    location_source: int = 0
    altitude_source: int = 0
    position_time: int = 0

@dataclass
class DeviceMetrics:
    """Device telemetry data."""
    battery_level: Optional[int] = None
    voltage: Optional[float] = None
    channel_utilization: Optional[float] = None
    air_util_tx: Optional[float] = None
    uptime_seconds: Optional[int] = None

@dataclass
class MeshPacket:
    """Meshtastic packet data."""
    packet_id: int
    from_node: int
    to_node: int
    channel: int = 0
    hop_limit: int = 3
    hop_start: int = 3
    rx_rssi: int = 0
    rx_snr: float = 0.0
    want_ack: bool = False
    via_mqtt: bool = False
    is_encrypted: bool = False
    priority: int = 0
    portnum: int = 0
    payload: bytes = b""

class MeshtasticDB:
    """Database manager for Meshtastic network data."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema if needed."""
        with self.get_connection() as conn:
            # Check if tables exist
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='sessions'
            """)
            
            if cursor.fetchone()[0] == 0:
                # Load and execute schema
                with open('schema.sql', 'r') as f:
                    schema_sql = f.read()
                conn.executescript(schema_sql)
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
        finally:
            conn.close()
    
    def get_active_session_id(self) -> int:
        """Get the currently active session ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM sessions WHERE is_active = 1")
            result = cursor.fetchone()
            return result[0] if result else self.create_session("Default Session")
    
    def create_session(self, name: str, description: str = "") -> int:
        """Create a new session and make it active."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Deactivate current session
            cursor.execute("""
                UPDATE sessions 
                SET is_active = 0, end_time = ? 
                WHERE is_active = 1
            """, (int(time.time()),))
            
            # Create new active session
            cursor.execute("""
                INSERT INTO sessions (name, start_time, is_active, description)
                VALUES (?, ?, 1, ?)
            """, (name, int(time.time()), description))
            
            conn.commit()
            return cursor.lastrowid
    
    def upsert_node(self, node_info: NodeInfo, session_id: Optional[int] = None) -> None:
        """Insert or update node information."""
        if session_id is None:
            session_id = self.get_active_session_id()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert lat/lon from protobuf format  
            current_time = int(time.time())
            
            cursor.execute("""
                INSERT INTO nodes (
                    id, session_id, short_name, long_name, is_licensed,
                    hardware_model_id, role_id, macaddr, first_seen, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id, session_id) DO UPDATE SET
                    short_name = excluded.short_name,
                    long_name = excluded.long_name,
                    is_licensed = excluded.is_licensed,
                    hardware_model_id = excluded.hardware_model_id,
                    role_id = excluded.role_id,
                    macaddr = excluded.macaddr,
                    last_updated = excluded.last_updated
            """, (
                node_info.id, session_id, node_info.short_name, node_info.long_name,
                node_info.is_licensed, node_info.hardware_model_id, node_info.role_id,
                node_info.macaddr, current_time, current_time
            ))
            
            conn.commit()
    
    def update_node_metrics(self, node_id: int, snr: float, rssi: int, 
                          hops_away: int = 0, channel: int = 0, 
                          via_mqtt: bool = False, session_id: Optional[int] = None) -> None:
        """Update node network metrics."""
        if session_id is None:
            session_id = self.get_active_session_id()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE nodes 
                SET snr = ?, rssi = ?, hops_away = ?, channel = ?, 
                    via_mqtt = ?, last_heard = ?, last_updated = ?
                WHERE id = ? AND session_id = ?
            """, (
                snr, rssi, hops_away, channel, via_mqtt,
                int(time.time()), int(time.time()), node_id, session_id
            ))
            conn.commit()
    
    def insert_position(self, node_id: int, position: Position, 
                       session_id: Optional[int] = None) -> None:
        """Insert or update node position."""
        if session_id is None:
            session_id = self.get_active_session_id()
        
        # Convert protobuf coordinates to decimal degrees
        latitude = position.latitude_i * 1e-7 if position.latitude_i != 0 else None
        longitude = position.longitude_i * 1e-7 if position.longitude_i != 0 else None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update current position
            cursor.execute("""
                INSERT INTO node_positions (
                    node_id, session_id, latitude_i, longitude_i, 
                    latitude, longitude, altitude, location_source,
                    altitude_source, position_time, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id, session_id) DO UPDATE SET
                    latitude_i = excluded.latitude_i,
                    longitude_i = excluded.longitude_i,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    altitude = excluded.altitude,
                    location_source = excluded.location_source,
                    altitude_source = excluded.altitude_source,
                    position_time = excluded.position_time,
                    timestamp = excluded.timestamp
            """, (
                node_id, session_id, position.latitude_i, position.longitude_i,
                latitude, longitude, position.altitude, position.location_source,
                position.altitude_source, position.position_time or int(time.time()),
                int(time.time())
            ))
            
            # Add to history if position changed significantly
            if latitude is not None and longitude is not None:
                cursor.execute("""
                    INSERT INTO position_history (
                        node_id, session_id, latitude_i, longitude_i,
                        latitude, longitude, altitude, location_source,
                        altitude_source, position_time, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_id, session_id, position.latitude_i, position.longitude_i,
                    latitude, longitude, position.altitude, position.location_source,
                    position.altitude_source, position.position_time or int(time.time()),
                    int(time.time())
                ))
            
            conn.commit()
    
    def insert_device_metrics(self, node_id: int, metrics: DeviceMetrics,
                            session_id: Optional[int] = None) -> None:
        """Insert device telemetry data."""
        if session_id is None:
            session_id = self.get_active_session_id()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO device_metrics (
                    node_id, session_id, battery_level, voltage,
                    channel_utilization, air_util_tx, uptime_seconds, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node_id, session_id, metrics.battery_level, metrics.voltage,
                metrics.channel_utilization, metrics.air_util_tx,
                metrics.uptime_seconds, int(time.time())
            ))
            conn.commit()
    
    def insert_packet(self, packet: MeshPacket, session_id: Optional[int] = None) -> int:
        """Insert mesh packet data."""
        if session_id is None:
            session_id = self.get_active_session_id()
        
        # Calculate payload hash for deduplication
        payload_hash = hashlib.sha256(packet.payload).hexdigest() if packet.payload else None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mesh_packets (
                    session_id, packet_id, from_node, to_node, channel,
                    hop_limit, hop_start, rx_rssi, rx_snr, want_ack,
                    via_mqtt, is_encrypted, priority, portnum,
                    payload_size, payload_hash, rx_time, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, packet.packet_id, packet.from_node, packet.to_node,
                packet.channel, packet.hop_limit, packet.hop_start,
                packet.rx_rssi, packet.rx_snr, packet.want_ack, packet.via_mqtt,
                packet.is_encrypted, packet.priority, packet.portnum,
                len(packet.payload), payload_hash, int(time.time()), int(time.time())
            ))
            
            packet_db_id = cursor.lastrowid
            
            # Update node link statistics
            self._update_node_link(
                packet.from_node, packet.to_node, packet.rx_rssi, 
                packet.rx_snr, packet.hop_limit, session_id, conn
            )
            
            conn.commit()
            return packet_db_id
    
    def insert_text_message(self, from_node: int, to_node: int, message: str,
                          channel: int = 0, packet_id: Optional[int] = None,
                          session_id: Optional[int] = None) -> None:
        """Insert text message."""
        if session_id is None:
            session_id = self.get_active_session_id()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO text_messages (
                    packet_id, session_id, from_node, to_node, channel,
                    message_text, is_broadcast, is_direct, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                packet_id, session_id, from_node, to_node, channel,
                message, to_node == 0, to_node != 0, int(time.time())
            ))
            conn.commit()
    
    def _update_node_link(self, from_node: int, to_node: int, rssi: int,
                         snr: float, hop_count: int, session_id: int,
                         conn: sqlite3.Connection) -> None:
        """Update node link statistics."""
        cursor = conn.cursor()
        
        # Get existing link stats
        cursor.execute("""
            SELECT packet_count, avg_rssi, avg_snr, avg_hop_count
            FROM node_links 
            WHERE session_id = ? AND from_node = ? AND to_node = ?
        """, (session_id, from_node, to_node))
        
        existing = cursor.fetchone()
        current_time = int(time.time())
        
        if existing:
            # Update existing link
            count = existing[0] + 1
            new_avg_rssi = ((existing[1] * existing[0]) + rssi) / count
            new_avg_snr = ((existing[2] * existing[0]) + snr) / count  
            new_avg_hops = ((existing[3] * existing[0]) + hop_count) / count
            
            cursor.execute("""
                UPDATE node_links 
                SET packet_count = ?, avg_rssi = ?, avg_snr = ?, 
                    avg_hop_count = ?, success_rate = 100.0,
                    is_direct = ?, last_seen = ?, last_updated = ?
                WHERE session_id = ? AND from_node = ? AND to_node = ?
            """, (
                count, new_avg_rssi, new_avg_snr, new_avg_hops,
                hop_count <= 1, current_time, current_time,
                session_id, from_node, to_node
            ))
        else:
            # Create new link
            cursor.execute("""
                INSERT INTO node_links (
                    session_id, from_node, to_node, packet_count,
                    success_rate, avg_rssi, avg_snr, avg_hop_count,
                    is_direct, last_seen, first_seen, last_updated
                ) VALUES (?, ?, ?, 1, 100.0, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, from_node, to_node, rssi, snr, hop_count,
                hop_count <= 1, current_time, current_time, current_time
            ))
    
    def get_active_nodes(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get nodes active within specified minutes."""
        cutoff_time = int(time.time()) - (minutes * 60)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM current_nodes 
                WHERE last_heard > ?
                ORDER BY last_heard DESC
            """, (cutoff_time,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_messages(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent text messages."""
        cutoff_time = int(time.time()) - (hours * 3600)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM recent_messages 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (cutoff_time, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_network_topology(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get active network links for topology visualization."""
        cutoff_time = int(time.time()) - (hours * 3600)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM network_topology 
                WHERE last_seen > ?
                ORDER BY packet_count DESC
            """, (cutoff_time,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_telemetry_data(self, node_id: int, hours: int = 24) -> Dict[str, List]:
        """Get telemetry data for a specific node."""
        cutoff_time = int(time.time()) - (hours * 3600)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Device metrics
            cursor.execute("""
                SELECT battery_level, voltage, channel_utilization, 
                       air_util_tx, uptime_seconds, timestamp
                FROM device_metrics 
                WHERE node_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (node_id, cutoff_time))
            
            device_metrics = [dict(row) for row in cursor.fetchall()]
            
            # Environment metrics
            cursor.execute("""
                SELECT temperature, relative_humidity, barometric_pressure,
                       lux, wind_speed, wind_direction, timestamp
                FROM environment_metrics
                WHERE node_id = ? AND timestamp > ?
                ORDER BY timestamp DESC  
            """, (node_id, cutoff_time))
            
            env_metrics = [dict(row) for row in cursor.fetchall()]
            
            return {
                'device_metrics': device_metrics,
                'environment_metrics': env_metrics
            }
    
    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Clean up data older than specified days."""
        cutoff_time = int(time.time()) - (days * 86400)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count records before deletion
            tables = [
                'position_history', 'device_metrics', 'environment_metrics',
                'power_metrics', 'mesh_packets', 'text_messages', 'packet_routes'
            ]
            
            deleted_counts = {}
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE timestamp < ?", (cutoff_time,))
                count_before = cursor.fetchone()[0]
                
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_time,))
                deleted_counts[table] = count_before - cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            
            conn.commit()
            
            # Vacuum to reclaim space
            conn.execute("VACUUM")
            
            return deleted_counts
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Database size
            cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()[0]
            
            # Table counts
            stats = {'database_size_mb': round(db_size / 1024 / 1024, 2)}
            
            tables = [
                'sessions', 'nodes', 'mesh_packets', 'text_messages',
                'node_positions', 'device_metrics', 'environment_metrics'
            ]
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f'{table}_count'] = cursor.fetchone()[0]
            
            return stats


def example_usage():
    """Example usage of the MeshtasticDB class."""
    
    # Initialize database
    db = MeshtasticDB('meshtastic_network.db')
    
    # Create a node
    node = NodeInfo(
        id=123456789,
        short_name="!a1b2c3d4",
        long_name="Solar Repeater North",
        hardware_model_id=4,  # T-Beam
        role_id=2  # Router
    )
    
    # Insert node
    db.upsert_node(node)
    
    # Add position
    position = Position(
        latitude_i=int(40.7128 * 1e7),  # NYC coordinates
        longitude_i=int(-74.0060 * 1e7),
        altitude=10,
        location_source=1  # GPS
    )
    
    db.insert_position(node.id, position)
    
    # Add device metrics
    metrics = DeviceMetrics(
        battery_level=85,
        voltage=3.7,
        channel_utilization=15.2,
        air_util_tx=2.1,
        uptime_seconds=86400
    )
    
    db.insert_device_metrics(node.id, metrics)
    
    # Add a packet
    packet = MeshPacket(
        packet_id=987654321,
        from_node=node.id,
        to_node=0,  # Broadcast
        rx_rssi=-50,
        rx_snr=8.5,
        portnum=1,  # TEXT_MESSAGE_APP
        payload=b"Hello mesh network!"
    )
    
    packet_db_id = db.insert_packet(packet)
    
    # Add text message
    db.insert_text_message(
        from_node=node.id,
        to_node=0,
        message="Hello mesh network!",
        packet_id=packet_db_id
    )
    
    # Query active nodes
    active_nodes = db.get_active_nodes(minutes=10)
    print(f"Active nodes: {len(active_nodes)}")
    
    # Query recent messages
    messages = db.get_recent_messages(hours=1)
    print(f"Recent messages: {len(messages)}")
    
    # Get database stats
    stats = db.get_database_stats()
    print(f"Database stats: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    example_usage()