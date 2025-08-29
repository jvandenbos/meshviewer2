# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real-time network visualizer for Meshtastic mesh networks with force-directed graph visualization, session management, and <100ms response times. Connects to RAK 4631 (or compatible devices) via USB-C to display live mesh network topology.

## Development Commands

### Quick Start
```bash
# Both services at once
./start.sh

# Or manually:
# Backend (Python virtual environment required)
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev
```

### Common Tasks
```bash
# Install/update dependencies
source venv/bin/activate && pip install -r requirements.txt
cd frontend && npm install

# Build frontend for production
cd frontend && npm run build

# Lint frontend
cd frontend && npm run lint

# Initialize/reset database
source venv/bin/activate
python3 -c "from backend.database import Database; import asyncio; asyncio.run(Database().initialize())"

# Create new session (clears UI, keeps archive)
curl -X POST http://localhost:8000/api/session/new
```

## Architecture

### Data Flow
1. **Meshtastic Device** (RAK 4631) → USB Serial → **Python Backend** (meshtastic_connector.py)
2. **Backend** processes packets via PubSub callbacks → stores in **SQLite** + broadcasts via **WebSocket**
3. **Frontend** receives WebSocket updates → updates **React state** → renders **Cytoscape.js graph**

### Session Management Design
- **UI displays only current session data** - provides clean, focused view
- **All data archived to SQLite** - complete history preserved
- **Session reset clears UI** but maintains database archive
- Only one active session at a time (enforced by unique constraint)

### WebSocket Protocol
Backend broadcasts these message types:
- `initial_state`: Full state dump on connection
- `node_info`: Node discovery/update
- `text_message`: Mesh messages
- `position_update`: GPS coordinates
- `telemetry`: Battery/voltage/metrics
- `network_link`: Topology connections
- `session_reset`: New session started

Frontend can send:
- `send_text`: Transmit message to mesh
- `request_telemetry`: Request node telemetry
- `request_position`: Request node position

### Critical Implementation Details

#### Broadcast Message Handling
- Meshtastic sends broadcast messages to ID `^all` or `4294967295`
- Backend maps these to `"broadcast"` string to avoid graph edge errors
- Frontend filters out broadcast links to prevent invalid edge creation

#### Type System
- All TypeScript interfaces defined in `/frontend/src/types/index.ts`
- Components import types from centralized location (not from websocket.ts)
- Prevents circular dependencies and module resolution issues

#### Async Event Loop
- Meshtastic callbacks run in separate thread without event loop
- Use `asyncio.get_event_loop()` check before `create_task()`
- Fallback to `asyncio.run()` if no loop available

#### Tailwind CSS Configuration
- **Must use Tailwind v3** - v4 has breaking PostCSS changes
- PostCSS config required at `/frontend/postcss.config.js`
- If styling breaks, check Tailwind version and PostCSS config

## Known Issues & Solutions

### WebSocket Connection Failures
- Backend may close connections during heavy packet flow
- Solution: Automatic reconnection with exponential backoff implemented

### JSON Serialization Errors
- Raw Meshtastic packet objects aren't JSON serializable
- Solution: Extract only serializable fields in `process_generic_packet()`

### Graph Rendering Errors
- Cytoscape throws error if edge references non-existent node
- Solution: Validate all nodes exist before creating edges in NetworkGraph component

### Missing Nodes in Graph
- Force-directed layout only shows nodes with edges
- Current implementation filters standalone nodes
- TODO: Add isolated node rendering support

## Database Schema

Key tables:
- `sessions`: Track visualization sessions
- `nodes`: Current node state per session
- `nodes_history`: Historical snapshots
- `mesh_packets`: All network packets
- `text_messages`: User messages
- `network_links`: Node connections
- `device_metrics`: Telemetry data

Indexes optimized for:
- Time-based queries: `(session_id, timestamp DESC)`
- Active node queries: `last_heard > cutoff`
- Network topology: Link quality and success rates

## Performance Requirements

- WebSocket latency: <100ms from packet receipt to UI update
- Node discovery: Immediate upon first packet
- Graph rendering: 60 FPS with 50+ nodes
- Database queries: <100ms for dashboard views

## Testing Checklist

When making changes, verify:
1. WebSocket connects and stays connected
2. Nodes appear in sidebar when discovered
3. Battery/signal indicators update correctly
4. Session reset clears UI but preserves database
5. Graph doesn't error on broadcast messages
6. Tailwind styles load (dark theme visible)
7. Event ticker shows activity
8. Connect/Disconnect buttons work