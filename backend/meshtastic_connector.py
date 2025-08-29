import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from datetime import datetime
from typing import Optional, Dict, Any, Callable
import asyncio
import time
import logging
from backend.models import NodeInfo, MeshPacket, TextMessage, NetworkLink

logger = logging.getLogger(__name__)

class MeshtasticConnector:
    def __init__(self, on_data_callback: Optional[Callable] = None):
        self.interface: Optional[meshtastic.serial_interface.SerialInterface] = None
        self.connected = False
        self.node_db: Dict[str, NodeInfo] = {}
        self.on_data_callback = on_data_callback
        self.local_node_id: Optional[str] = None
        
    def connect(self, device_path: Optional[str] = None) -> bool:
        """Connect to RAK 4631 over USB-C"""
        try:
            # Set up event handlers
            pub.subscribe(self.on_receive, "meshtastic.receive")
            pub.subscribe(self.on_connection, "meshtastic.connection.established")
            pub.subscribe(self.on_connection_lost, "meshtastic.connection.lost")
            
            # Connect to device
            if device_path:
                self.interface = meshtastic.serial_interface.SerialInterface(devPath=device_path)
            else:
                # Auto-detect RAK 4631
                self.interface = meshtastic.serial_interface.SerialInterface()
            
            self.connected = True
            logger.info(f"Connected to Meshtastic device")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from device"""
        if self.interface:
            self.interface.close()
            self.connected = False
            logger.info("Disconnected from Meshtastic device")
    
    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        """Called when connection is established"""
        logger.info("Meshtastic connection established")
        
        # Get local node info
        if hasattr(interface, 'myInfo') and interface.myInfo:
            self.local_node_id = str(interface.myInfo.my_node_num)
            logger.info(f"Local node ID: {self.local_node_id}")
            
            # Create entry for local node
            self.node_db[self.local_node_id] = {
                "id": self.local_node_id,
                "short_name": interface.myInfo.user.shortName if hasattr(interface.myInfo, 'user') else "My Node",
                "long_name": interface.myInfo.user.longName if hasattr(interface.myInfo, 'user') else "Local Meshtastic Node",
                "hardware_model": str(interface.myInfo.user.hwModel) if hasattr(interface.myInfo, 'user') else "Local Device",
                "role": "CLIENT",
                "hop_count": 0,  # Local node is always 0 hops
                "is_local": True
            }
            
            # Send local node info to backend
            if self.on_data_callback:
                local_node_data = {
                    "type": "node_info",
                    "node": self.node_db[self.local_node_id],
                    "hop_count": 0,
                    "timestamp": datetime.now()
                }
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.on_data_callback(local_node_data))
                except RuntimeError:
                    asyncio.run(self.on_data_callback(local_node_data))
        
        # Request initial data
        if self.interface:
            self.interface.sendText("Visualizer connected")
    
    def on_connection_lost(self, interface, topic=pub.AUTO_TOPIC):
        """Called when connection is lost"""
        logger.warning("Meshtastic connection lost")
        self.connected = False
        
        if self.on_data_callback:
            asyncio.create_task(self.on_data_callback({
                "type": "connection_lost",
                "timestamp": datetime.now()
            }))
    
    def on_receive(self, packet, interface):
        """Process incoming packets in real-time (<100ms)"""
        start_time = time.time()
        
        try:
            # Extract packet data - handle different packet structures
            packet_dict = packet.get('decoded', packet)
            
            # Try different fields for from_id
            from_id = packet.get('fromId') or packet.get('from')
            if not from_id and 'fromId' in str(packet):
                # Sometimes it's in the string representation
                from_id = self.local_node_id
            from_id = str(from_id) if from_id else self.local_node_id
            
            # Try different fields for to_id
            to_id_raw = packet.get('toId') or packet.get('to') or '^all'
            
            # Log raw packet info
            logger.info(f"📡 Packet from {from_id[:8] if from_id else 'Unknown'} to {to_id_raw[:8] if isinstance(to_id_raw, str) else to_id_raw}")
            # Handle special broadcast IDs
            if to_id_raw == '^all' or str(to_id_raw) == '4294967295':
                to_id = 'broadcast'
            else:
                to_id = str(to_id_raw)
            
            # Process based on packet type
            data = None
            packet_type = packet_dict.get('portnum', 'UNKNOWN')
            
            # Log with correct hop calculation
            hop_count_log = (packet.get('hopStart', 0) - packet.get('hopLimit', 0)) if packet.get('hopStart', 0) > 0 else 0
            rssi_log = packet.get('rxRssi') or packet.get('rx_rssi')
            snr_log = packet.get('rxSnr') or packet.get('rx_snr')
            logger.info(f"   Type: {packet_type}, RSSI: {rssi_log}, SNR: {snr_log}, Hops: {hop_count_log}")
            
            if packet_type == 'TEXT_MESSAGE_APP':
                data = self.process_text_message(packet_dict, from_id, to_id)
            elif packet_type == 'POSITION_APP':
                logger.info(f"   📍 Position update from {from_id[:8]}")
                data = self.process_position(packet_dict, from_id)
            elif packet_type == 'NODEINFO_APP':
                logger.info(f"   👤 Node info from {from_id[:8]}")
                data = self.process_node_info(packet_dict, from_id)
            elif packet_type == 'TELEMETRY_APP':
                logger.info(f"   📊 Telemetry from {from_id[:8]}")
                data = self.process_telemetry(packet_dict, from_id)
            else:
                data = self.process_generic_packet(packet_dict, from_id, to_id)
            
            # Add common packet info
            if data:
                # Calculate hop count correctly: hopStart - hopLimit
                # hopStart is the initial value (e.g., 3), hopLimit decreases with each hop
                hop_start = packet.get('hopStart', 0)
                hop_limit = packet.get('hopLimit', 0)
                # Only calculate if we have hop information, otherwise use None
                if hop_start > 0:
                    hop_count = hop_start - hop_limit
                else:
                    # No hop information available - could be direct connection or unknown
                    hop_count = None
                
                data.update({
                    "rssi": packet.get('rxRssi') or packet.get('rx_rssi'),  # Try both camelCase and snake_case
                    "snr": packet.get('rxSnr') or packet.get('rx_snr'),
                    "hop_count": hop_count,
                    "channel": packet.get('channel', 0)
                })
                
                # Update network topology
                if from_id != self.local_node_id:
                    self.update_network_link(from_id, to_id, data)
                
                # Send to callback
                if self.on_data_callback:
                    logger.info(f"   ✅ Sending {data['type']} to backend for node {data.get('node_id', data.get('node', {}).get('id', 'unknown'))}")
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self.on_data_callback(data))
                        else:
                            asyncio.run(self.on_data_callback(data))
                    except RuntimeError:
                        # If no event loop, create one
                        asyncio.run(self.on_data_callback(data))
            
            # Performance monitoring
            processing_time = (time.time() - start_time) * 1000
            if processing_time > 50:  # Warning if approaching 100ms limit
                logger.warning(f"Packet processing time: {processing_time:.1f}ms")
                
        except Exception as e:
            logger.error(f"Error processing packet: {e}")
    
    def process_text_message(self, packet: Dict, from_id: str, to_id: str) -> Dict:
        """Process text message packet"""
        message = packet.get('text', '')
        from_name = self.node_db.get(from_id, {}).get('short_name', f"Node-{from_id}")
        to_name = self.node_db.get(to_id, {}).get('short_name', "All" if to_id == "4294967295" else f"Node-{to_id}")
        
        return {
            "type": "text_message",
            "from_id": from_id,
            "from_name": from_name,
            "to_id": to_id,
            "to_name": to_name,
            "message": message,
            "timestamp": datetime.now()
        }
    
    def process_position(self, packet: Dict, from_id: str) -> Dict:
        """Process position packet"""
        position = packet.get('position', {})
        
        # Update node database
        if from_id not in self.node_db:
            self.node_db[from_id] = {}
        
        self.node_db[from_id].update({
            "latitude": position.get('latitudeI', 0) / 1e7 if 'latitudeI' in position else None,
            "longitude": position.get('longitudeI', 0) / 1e7 if 'longitudeI' in position else None,
            "altitude": position.get('altitude', 0)
        })
        
        return {
            "type": "position_update",
            "node_id": from_id,
            "latitude": self.node_db[from_id].get("latitude"),
            "longitude": self.node_db[from_id].get("longitude"),
            "altitude": self.node_db[from_id].get("altitude"),
            "timestamp": datetime.now()
        }
    
    def process_node_info(self, packet: Dict, from_id: str) -> Dict:
        """Process node info packet"""
        user = packet.get('user', {})
        
        # Update node database
        if from_id not in self.node_db:
            self.node_db[from_id] = {}
        
        # Handle hardware model - convert int to string if needed
        hw_model = user.get('hwModel', 'UNSET')
        if isinstance(hw_model, int):
            # Convert hardware model ID to string
            hw_model = str(hw_model)
        
        # Handle role - convert int to string if needed
        role = user.get('role', 'CLIENT')
        if isinstance(role, int):
            # Map role numbers to role names (based on Meshtastic protobuf)
            role_map = {
                0: 'CLIENT',
                1: 'CLIENT_MUTE', 
                2: 'ROUTER',
                3: 'ROUTER_CLIENT',
                4: 'REPEATER',
                11: 'TRACKER'  # New role type
            }
            role = role_map.get(role, 'CLIENT')
        
        self.node_db[from_id].update({
            "id": from_id,
            "short_name": user.get('shortName', f"Node-{from_id}"),
            "long_name": user.get('longName', ''),
            "hardware_model": hw_model,
            "role": role,
            "is_licensed": user.get('isLicensed', False)
        })
        
        logger.info(f"      Node DB updated: {from_id[:8]} = {user.get('shortName', 'Unknown')}, role={role}, hw={hw_model}")
        
        return {
            "type": "node_info",
            "node": self.node_db[from_id],
            "timestamp": datetime.now()
        }
    
    def process_telemetry(self, packet: Dict, from_id: str) -> Dict:
        """Process telemetry packet"""
        telemetry = packet.get('telemetry', {})
        
        # Device metrics
        device_metrics = telemetry.get('deviceMetrics', {})
        
        # Update node database
        if from_id not in self.node_db:
            self.node_db[from_id] = {}
        
        self.node_db[from_id].update({
            "battery_level": device_metrics.get('batteryLevel'),
            "voltage": device_metrics.get('voltage'),
            "channel_utilization": device_metrics.get('channelUtilization'),
            "air_util_tx": device_metrics.get('airUtilTx'),
            "uptime_seconds": device_metrics.get('uptimeSeconds')
        })
        
        logger.info(f"      Telemetry updated: {from_id[:8]} battery={device_metrics.get('batteryLevel')}%, voltage={device_metrics.get('voltage')}V")
        
        # Environment metrics
        env_metrics = telemetry.get('environmentMetrics', {})
        if env_metrics:
            self.node_db[from_id].update({
                "temperature": env_metrics.get('temperature'),
                "humidity": env_metrics.get('relativeHumidity'),
                "pressure": env_metrics.get('barometricPressure')
            })
        
        return {
            "type": "telemetry",
            "node_id": from_id,
            "device_metrics": device_metrics,
            "environment_metrics": env_metrics,
            "timestamp": datetime.now()
        }
    
    def process_generic_packet(self, packet: Dict, from_id: str, to_id: str) -> Dict:
        """Process generic packet"""
        # Only include serializable payload data
        safe_payload = {}
        if isinstance(packet, dict):
            for key, value in packet.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    safe_payload[key] = value
                elif isinstance(value, (list, dict)):
                    safe_payload[key] = str(value)
        
        return {
            "type": "mesh_packet",
            "from_id": from_id,
            "to_id": to_id,
            "packet_type": packet.get('portnum', 'UNKNOWN'),
            "payload": safe_payload,
            "timestamp": datetime.now()
        }
    
    def update_network_link(self, from_id: str, to_id: str, packet_data: Dict):
        """Update network topology based on packet routing"""
        # This is called for each packet to build network topology
        # The actual link data would be sent via callback
        link_data = {
            "type": "network_link",
            "from_id": from_id,
            "to_id": to_id if to_id not in ["4294967295", "^all"] else str(self.local_node_id) if self.local_node_id else "broadcast",  # Broadcast handling
            "rssi": packet_data.get("rssi"),
            "snr": packet_data.get("snr"),
            "is_direct": packet_data.get("hop_count") == 1,  # Direct connections are 1 hop
            "timestamp": datetime.now()
        }
        
        if self.on_data_callback:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.on_data_callback(link_data))
                else:
                    asyncio.run(self.on_data_callback(link_data))
            except RuntimeError:
                asyncio.run(self.on_data_callback(link_data))
    
    def send_text(self, text: str, destination: Optional[str] = None) -> bool:
        """Send text message"""
        if not self.interface or not self.connected:
            return False
        
        try:
            if destination:
                self.interface.sendText(text, destinationId=destination)
            else:
                self.interface.sendText(text)
            return True
        except Exception as e:
            logger.error(f"Failed to send text: {e}")
            return False
    
    def request_telemetry(self, node_id: Optional[str] = None):
        """Request telemetry from a node"""
        if not self.interface or not self.connected:
            return
        
        try:
            if node_id:
                self.interface.requestTelemetry(destinationId=node_id)
            else:
                self.interface.requestTelemetry()
        except Exception as e:
            logger.error(f"Failed to request telemetry: {e}")
    
    def request_position(self, node_id: Optional[str] = None):
        """Request position from a node"""
        if not self.interface or not self.connected:
            return
        
        try:
            if node_id:
                self.interface.requestPosition(destinationId=node_id)
            else:
                self.interface.requestPosition()
        except Exception as e:
            logger.error(f"Failed to request position: {e}")
    
    def get_node_info(self, node_id: str) -> Optional[Dict]:
        """Get cached node information"""
        return self.node_db.get(node_id)
    
    def get_all_nodes(self) -> Dict[str, Dict]:
        """Get all cached nodes"""
        return self.node_db.copy()