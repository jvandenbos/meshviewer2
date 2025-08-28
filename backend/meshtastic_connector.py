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
            # Extract packet data
            packet_dict = packet.get('decoded', packet)
            from_id = str(packet.get('fromId', packet.get('from', '')))
            to_id_raw = packet.get('toId', packet.get('to', ''))
            # Handle special broadcast IDs
            if to_id_raw == '^all' or str(to_id_raw) == '4294967295':
                to_id = 'broadcast'
            else:
                to_id = str(to_id_raw)
            
            # Process based on packet type
            data = None
            packet_type = packet_dict.get('portnum', 'UNKNOWN')
            
            if packet_type == 'TEXT_MESSAGE_APP':
                data = self.process_text_message(packet_dict, from_id, to_id)
            elif packet_type == 'POSITION_APP':
                data = self.process_position(packet_dict, from_id)
            elif packet_type == 'NODEINFO_APP':
                data = self.process_node_info(packet_dict, from_id)
            elif packet_type == 'TELEMETRY_APP':
                data = self.process_telemetry(packet_dict, from_id)
            else:
                data = self.process_generic_packet(packet_dict, from_id, to_id)
            
            # Add common packet info
            if data:
                data.update({
                    "rssi": packet.get('rssi'),
                    "snr": packet.get('snr'),
                    "hop_count": packet.get('hopLimit', 0) - packet.get('hopStart', 0),
                    "channel": packet.get('channel', 0)
                })
                
                # Update network topology
                if from_id != self.local_node_id:
                    self.update_network_link(from_id, to_id, data)
                
                # Send to callback
                if self.on_data_callback:
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
        
        self.node_db[from_id].update({
            "id": from_id,
            "short_name": user.get('shortName', f"Node-{from_id}"),
            "long_name": user.get('longName', ''),
            "hardware_model": user.get('hwModel', 'UNSET'),
            "role": user.get('role', 'CLIENT'),
            "is_licensed": user.get('isLicensed', False)
        })
        
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
            "is_direct": packet_data.get("hop_count", 0) == 0,
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