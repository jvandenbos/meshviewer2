# Meshtastic Visualizer Architecture Plan

## **Recommended Technology Stack**
- **Backend**: FastAPI + WebSocket for real-time data streaming
- **Frontend**: React + TypeScript + Cytoscape.js (WebGPU renderer)
- **Database**: SQLite with session-based architecture
- **Meshtastic Integration**: Python `meshtastic.serial_interface` with PubSub callbacks

## **Core Architecture Components**

### **1. Data Layer**
- **LiveSessionManager**: Session start/reset, only show current session in UI
- **MeshtasticConnector**: RAK 4631 USB-C interface with <100ms response callbacks
- **SQLiteArchiver**: All data archived to SQLite for future analysis
- **Real-time Events**: PubSub system for node discovery, messages, telemetry

### **2. Visualization Layer** 
- **Force-Directed Graph**: Cytoscape.js with WebGPU for 50+ nodes
- **Animation System**: Node discovery fade-ins, packet flow tracers, connection pulses
- **Color Psychology**: Green(excellent) → Yellow(good) → Orange(weak) → Red(poor) signal
- **Interactive Features**: Hover tooltips, click handlers, time scrubber

### **3. UI Components**
- **Main Topology View**: Center stage force-directed graph
- **Live Sidebar**: Active nodes sorted by activity 
- **Event Ticker**: Scrolling live events (messages, discoveries)
- **Session Controls**: Start/reset session functionality

## **Implementation Phases**

### **Phase 1**: Core Infrastructure (Days 1-2)
1. FastAPI backend with Meshtastic USB-C integration
2. SQLite schema with session management
3. Basic React frontend with Cytoscape.js
4. WebSocket real-time data pipeline

### **Phase 2**: Live Visualization (Days 3-4)
1. Force-directed graph with node discovery animations  
2. Color-coded signal strength/battery visualization
3. Interactive hover/click features
4. Session start/reset functionality

### **Phase 3**: Advanced Features (Days 5-6)
1. Packet flow tracer animations
2. Link thickness based on signal strength
3. Event ticker and activity-based sidebar
4. Time scrubber for 60-second replay

### **Phase 4**: Polish & Performance (Day 7)
1. WebGPU renderer optimization
2. Visual effects (glows, pulses)
3. Performance monitoring (<100ms guarantee)
4. Production deployment setup

## **Key Technical Decisions**
- **Session-based data**: UI only shows current session, everything archived to SQLite
- **Real-time architecture**: WebSocket + PubSub for <100ms updates
- **Cytoscape.js WebGPU**: Future-proof, handles massive networks
- **Python backend**: Direct Meshtastic API integration, familiar ecosystem

## **Research Summary**

### **Meshtastic Python API**
- **Connection**: `meshtastic.serial_interface.SerialInterface()` for RAK 4631 USB-C
- **Real-time**: PubSub callbacks for <100ms response (`pub.subscribe(onReceive, "meshtastic.receive")`)
- **Data Available**: RSSI, SNR, hop count, battery level, GPS position, hardware model, node role
- **Session Management**: Built-in connection management with auto-reconnection

### **Frontend Framework Analysis**
- **Winner**: FastAPI + React + Cytoscape.js
  - WebGL/WebGPU rendering for 50+ nodes
  - WebSocket for real-time updates
  - Proven in production Meshtastic visualizers
  - Rich animation and interaction capabilities

### **Database Design**
- **Session-based**: Active session for UI, archived sessions for analysis
- **Tables**: nodes, mesh_packets, text_messages, telemetry metrics, network topology
- **Optimized**: Indexes for time-based queries, pre-built views for dashboard
- **Performance**: <100ms dashboard queries, <1s historical analysis

### **Animation Libraries**
- **Cytoscape.js**: Best overall - WebGPU support, force-directed layouts, rich animations
- **Alternative**: Sigma.js for pure WebGL performance
- **Python**: Dash Cytoscape for Python-centric development

## **File Structure**
```
meshtastic-visualizer/
├── backend/
│   ├── main.py                 # FastAPI server with WebSocket
│   ├── meshtastic_connector.py # RAK 4631 USB interface
│   ├── session_manager.py      # Live session management
│   ├── database.py             # SQLite operations
│   └── models.py               # Pydantic models
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main React app
│   │   ├── components/
│   │   │   ├── NetworkGraph.tsx    # Cytoscape.js force-directed graph
│   │   │   ├── ActiveNodes.tsx     # Live sidebar
│   │   │   ├── EventTicker.tsx     # Scrolling events
│   │   │   └── SessionControls.tsx # Start/reset session
│   │   ├── services/
│   │   │   └── websocket.ts    # Real-time data connection
│   │   └── styles/              # Visual theming
│   └── package.json
├── database/
│   └── schema.sql               # SQLite schema
└── requirements.txt             # Python dependencies
```

## **Key Implementation Patterns**

### **Real-time Data Flow**
```python
# Backend (FastAPI)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    def on_meshtastic_receive(packet, interface):
        # <100ms processing
        data = process_packet(packet)
        await websocket.send_json(data)
    
    pub.subscribe(on_meshtastic_receive, "meshtastic.receive")
```

### **Force-Directed Graph**
```typescript
// Frontend (React + Cytoscape.js)
const cy = cytoscape({
  container: containerRef.current,
  style: [
    {
      selector: 'node',
      style: {
        'background-color': (ele) => getSignalColor(ele.data('rssi')),
        'width': (ele) => getBatterySize(ele.data('battery')),
        'label': 'data(name)'
      }
    }
  ],
  layout: {
    name: 'cose',
    animate: true,
    animationDuration: 500
  }
});
```

### **Session Management**
```python
class SessionManager:
    def start_session(self):
        # Clear UI state
        self.active_nodes = {}
        self.active_messages = []
        
        # Create new session in DB
        session_id = create_session()
        
        # Archive continues in background
        return session_id
    
    def get_active_data(self):
        # Return only current session data for UI
        return self.active_nodes, self.active_messages
```

## **Performance Guarantees**
- **Update Latency**: <100ms from packet receipt to UI update
- **Animation Smoothness**: 60 FPS with 50+ nodes
- **Database Queries**: <100ms for live dashboard
- **WebSocket Overhead**: <10ms for message delivery
- **Memory Usage**: <500MB with 100 nodes active

## **Development Priorities**
1. **Core Functionality First**: Get basic visualization working
2. **Performance Second**: Optimize for <100ms updates
3. **Polish Last**: Advanced animations and visual effects
4. **Testing Throughout**: Real device testing with RAK 4631

This architecture provides a solid foundation for building a production-quality Meshtastic network visualizer with real-time updates, beautiful animations, and comprehensive data management.