# Meshtastic Network Visualizer Database Design

## Overview

This SQLite schema is optimized for storing and visualizing Meshtastic mesh network data with a focus on:
- **Real-time performance**: Fast queries for live dashboard updates
- **Historical archival**: Efficient storage of long-term network data  
- **Visualization support**: Query patterns optimized for network topology, message flows, and telemetry charts
- **Data integrity**: Foreign key constraints and proper normalization
- **Scalability**: Indexed tables supporting thousands of nodes and millions of packets

## Architecture Decisions

### Session-Based Data Management
The schema uses a session-based approach to separate current active data from historical archives:

- **Current Session**: Fast queries, frequent updates, optimized indexes
- **Historical Sessions**: Archived data for long-term analysis and trends
- **Only one active session** at a time (enforced by unique constraint)

This design enables:
- Fast real-time queries without scanning millions of historical records
- Clean data archival without losing historical context
- Easy session management and cleanup

### Normalization vs Performance Trade-offs

**Normalized Tables**: 
- `hardware_models`, `node_roles`: Referenced frequently, small lookup tables
- `sessions`: Clean session management

**Partially Denormalized**: 
- `mesh_packets`: Contains routing info directly for fast topology queries
- `nodes_history`: Denormalizes hardware_model/role names for archival independence

**Performance Optimized**:
- Current position stored separately from position history
- Latest telemetry accessible through views without complex aggregations
- Redundant timestamp fields where needed for different query patterns

### Index Strategy

Indexes are designed around common query patterns:

1. **Time-based queries**: All major tables indexed by `(session_id, timestamp DESC)`
2. **Node-centric queries**: Indexes on `node_id` combined with time
3. **Network topology**: Optimized for graph traversal and link analysis
4. **Real-time dashboard**: Fast active node identification

## Table Descriptions

### Core Tables

#### `sessions`
Manages data lifecycle and enables clean archival:
- **Active session**: `is_active = 1` (unique constraint ensures only one)
- **Archived sessions**: Historical data with start/end times
- **Cleanup strategy**: Delete sessions older than retention period

#### `nodes` 
Current node information optimized for real-time queries:
- **Composite primary key**: `(id, session_id)` allows same node ID across sessions
- **Latest metrics**: SNR, RSSI, battery level for dashboard display
- **Status tracking**: Last heard, hop count, connection flags

#### `nodes_history`
Archived node state snapshots:
- **Denormalized**: Hardware model and role stored as text for archival independence
- **Timeline tracking**: Historical view of node configuration changes

### Position & Location

#### `node_positions`
Current GPS position for each node:
- **Raw protobuf values**: `latitude_i`, `longitude_i` (sfixed32 from Meshtastic)
- **Calculated values**: `latitude`, `longitude` (multiplied by 1e-7)
- **Metadata**: Location source, precision, timing information

#### `position_history`  
Movement tracking and historical positions:
- **High frequency**: Can store frequent position updates
- **Mapping support**: Enables track/trail visualization
- **Cleanup**: Configurable retention for managing storage

### Telemetry Data

#### `device_metrics`
Core device health information:
- **Battery monitoring**: Level, voltage, external power detection  
- **Network utilization**: Channel usage, airtime tracking
- **System health**: Uptime tracking

#### `environment_metrics`
Environmental sensor readings:
- **Weather data**: Temperature, humidity, pressure, wind
- **Air quality**: Gas sensors, particulate matter, IAQ
- **Light sensors**: Ambient, UV, IR measurements
- **Other sensors**: Distance, weight, soil monitoring, radiation

#### `power_metrics`
Multi-channel power monitoring:
- **8 channels**: Voltage/current pairs for complex power systems
- **Solar/battery systems**: Multiple power source monitoring
- **Load analysis**: Power consumption tracking

### Messages & Packets

#### `mesh_packets`
All network packets for topology analysis:
- **Routing information**: Hop counts, relay paths, next hop
- **RF metrics**: RSSI, SNR at reception  
- **Metadata**: Priority, encryption status, MQTT bridge info
- **Deduplication**: Payload hash for identifying duplicates

#### `text_messages`  
User text messages:
- **Linked to packets**: References `mesh_packets.id`
- **Message types**: Broadcast vs direct messages
- **Content**: Full message text with metadata

#### `packet_routes`
Multi-hop routing path tracking:
- **Hop-by-hop**: Each node in route with RF metrics
- **Network analysis**: Path optimization and failure analysis
- **Performance**: Link quality assessment

### Network Topology

#### `node_links`
Node-to-node connection quality:
- **Link metrics**: Success rate, average RSSI/SNR, hop count
- **Temporal data**: First seen, last seen, packet counts
- **Direct vs multi-hop**: Connection type classification

#### `node_neighbors` 
Direct neighbor relationships:
- **Immediate connections**: Single-hop neighbors only
- **Signal quality**: SNR to each neighbor
- **Network mapping**: Physical proximity inference

## Query Patterns & Performance

### Real-time Dashboard (< 100ms)
- Active nodes: `WHERE last_heard > (unixepoch() - 300)`
- Current metrics: Pre-calculated in views
- Network status: Aggregated statistics

### Historical Analysis (< 1s)
- Time series data: Indexed timestamp columns
- Node tracking: Position and metric history
- Message flows: Temporal message analysis

### Network Topology (< 500ms)
- Link analysis: `node_links` with aggregated metrics  
- Route discovery: `packet_routes` hop tracking
- Centrality analysis: Connection counting

### Geographical Visualization (< 200ms)
- Active positions: `current_nodes` view with coordinates
- Movement tracking: `position_history` with time filtering
- Distance calculations: Haversine formula in SQL

## Data Cleanup Strategies

### Automated Cleanup
1. **Session Archival**: Move current session to history when inactive
2. **Old Data Pruning**: Delete data older than retention period
3. **Duplicate Removal**: Use payload hashes to identify duplicates
4. **Index Maintenance**: Regular ANALYZE and occasional VACUUM

### Storage Management
- **Partition by time**: Session-based partitioning  
- **Compress old data**: Consider external archival for very old sessions
- **Monitor growth**: Track table sizes and query performance

### Retention Policies
- **Active session**: Keep all data for real-time queries
- **Recent history**: 30 days of detailed packet/telemetry data
- **Long-term archive**: Summarized data for trend analysis
- **Configuration**: Adjustable retention periods per data type

## Schema Evolution

### Version Management
- **Schema versioning**: Add version table for migrations
- **Backward compatibility**: Careful column additions
- **Data migration**: Scripts for schema updates

### Future Enhancements
- **Sharding**: Multiple database files for very large deployments
- **Compression**: Compressed telemetry storage for long-term data
- **External storage**: Blob storage for large payloads (images, files)
- **Real-time views**: Materialized views for complex dashboard queries

## Integration Notes

### Meshtastic Protobuf Mapping
- **MeshPacket**: Maps to `mesh_packets` table
- **NodeInfo**: Combination of `nodes` + `node_positions` + latest telemetry  
- **Position**: Direct mapping to position tables with coordinate conversion
- **Telemetry**: Separated by type into device/environment/power metrics

### Performance Considerations
- **WAL mode**: Better concurrency for reads during writes
- **Connection pooling**: Multiple readers, single writer pattern
- **Prepared statements**: Avoid SQL injection and improve performance
- **Batch inserts**: Transaction batching for high-frequency data

### Visualization Framework Integration
- **Views**: Pre-built views for common dashboard queries
- **JSON output**: Easy conversion to web-friendly formats  
- **Real-time updates**: Efficient polling queries for live updates
- **Caching**: Application-level caching for frequently accessed data

## Security Considerations

### Data Privacy  
- **Node anonymization**: Option to hash/obscure node IDs
- **Message content**: Consider encryption for sensitive messages
- **Location privacy**: Configurable position data retention

### Access Control
- **Read-only connections**: Separate connection strings for visualization
- **Data export**: Controlled access to historical data
- **Audit trails**: Track data access and modifications

This schema provides a robust foundation for Meshtastic network visualization while maintaining performance and scalability for real-world deployments.