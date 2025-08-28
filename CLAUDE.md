# Meshtastic Visualizer Project

## Project Overview
Building a real-time network visualizer for Meshtastic mesh networks with force-directed graph visualization, session management, and <100ms response times.

## Technology Stack
- **Backend**: FastAPI + WebSocket + Python Meshtastic API
- **Frontend**: React + TypeScript + Cytoscape.js (WebGPU)
- **Database**: SQLite with session-based architecture
- **Device**: RAK 4631 connected via USB-C

## Current Status
- [x] Research completed for all components
- [x] Architecture plan created (see ARCHITECTURE.md)
- [ ] Phase 1: Core Infrastructure implementation
- [ ] Phase 2: Live Visualization
- [ ] Phase 3: Advanced Features
- [ ] Phase 4: Polish & Performance

## Key Requirements
- Session-based UI (only show current session data)
- All data archived to SQLite for analysis
- <100ms real-time updates
- Force-directed graph visualization (not radar/radial)
- Animations: node discovery, packet flow, connection pulses
- Color-coded signal strength and battery levels

## Development Commands
```bash
# Backend
pip install fastapi uvicorn meshtastic sqlite3 websockets
uvicorn backend.main:app --reload --port 8000

# Frontend
npm install
npm run dev

# Database
sqlite3 meshtastic.db < database/schema.sql
```

## File Structure
```
meshtastic-visualizer/
├── ARCHITECTURE.md     # Detailed architecture plan
├── CLAUDE.md          # This file - project overview
├── backend/           # FastAPI + Meshtastic integration
├── frontend/          # React + Cytoscape.js UI
└── database/          # SQLite schema and queries
```