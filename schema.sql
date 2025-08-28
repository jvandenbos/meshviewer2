-- Meshtastic Network Visualizer SQLite Schema
-- Optimized for real-time updates and historical archival
-- Based on Meshtastic protobuf definitions and community best practices

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = memory;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Sessions table for managing current vs archived data
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_time INTEGER NOT NULL, -- Unix timestamp
    end_time INTEGER,            -- NULL for active session
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
    UNIQUE(is_active) WHERE is_active = 1 -- Only one active session
);

-- Hardware models enum table
CREATE TABLE hardware_models (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL
);

-- Node roles enum table  
CREATE TABLE node_roles (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

-- ============================================================================
-- NODE MANAGEMENT
-- ============================================================================

-- Core node information - normalized for current session
CREATE TABLE nodes (
    id INTEGER NOT NULL,           -- Meshtastic node ID (fixed32)
    session_id INTEGER NOT NULL,
    
    -- User information
    short_name TEXT,               -- Display name for UI
    long_name TEXT,                -- Full name/callsign
    is_licensed BOOLEAN DEFAULT 0, -- Ham radio license
    
    -- Hardware information
    hardware_model_id INTEGER,
    role_id INTEGER DEFAULT 1,     -- CLIENT role by default
    macaddr TEXT,                  -- MAC address (6 bytes hex)
    
    -- Network metrics (latest values)
    last_heard INTEGER,            -- Unix timestamp
    snr REAL,                      -- Signal to noise ratio
    rssi INTEGER,                  -- Received signal strength
    hops_away INTEGER DEFAULT 0,   -- Hop count from gateway
    channel INTEGER DEFAULT 0,    -- Channel number
    via_mqtt BOOLEAN DEFAULT 0,   -- Received via MQTT
    
    -- Status flags
    is_favorite BOOLEAN DEFAULT 0,
    is_ignored BOOLEAN DEFAULT 0,
    is_key_verified BOOLEAN DEFAULT 0,
    
    -- Timestamps
    first_seen INTEGER NOT NULL DEFAULT (unixepoch()),
    last_updated INTEGER NOT NULL DEFAULT (unixepoch()),
    
    PRIMARY KEY (id, session_id),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (hardware_model_id) REFERENCES hardware_models(id),
    FOREIGN KEY (role_id) REFERENCES node_roles(id)
);

-- Historical node information - denormalized for archival
CREATE TABLE nodes_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    
    -- Snapshot of node state at this time
    short_name TEXT,
    long_name TEXT,
    hardware_model TEXT,          -- Denormalized for archival
    role TEXT,                    -- Denormalized for archival
    
    snr REAL,
    rssi INTEGER,
    hops_away INTEGER,
    channel INTEGER,
    via_mqtt BOOLEAN,
    
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- ============================================================================
-- POSITION & LOCATION
-- ============================================================================

-- Current position for each node
CREATE TABLE node_positions (
    node_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    
    -- Position data (Meshtastic uses sfixed32 * 1e-7 for lat/lon)
    latitude_i INTEGER,           -- Raw protobuf value
    longitude_i INTEGER,          -- Raw protobuf value  
    latitude REAL,                -- Calculated value (latitude_i * 1e-7)
    longitude REAL,               -- Calculated value (longitude_i * 1e-7)
    altitude INTEGER,             -- Meters above sea level
    
    -- Metadata
    location_source INTEGER DEFAULT 0,  -- GPS, manual, etc.
    altitude_source INTEGER DEFAULT 0,
    precision_bits INTEGER DEFAULT 32,  -- Position precision
    
    -- Timestamps
    position_time INTEGER,        -- When position was recorded
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()), -- When received
    
    PRIMARY KEY (node_id, session_id),
    FOREIGN KEY (node_id, session_id) REFERENCES nodes(id, session_id) ON DELETE CASCADE
);

-- Position history for tracking movement
CREATE TABLE position_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    
    latitude_i INTEGER,
    longitude_i INTEGER,
    latitude REAL,
    longitude REAL,
    altitude INTEGER,
    
    location_source INTEGER,
    altitude_source INTEGER,
    position_time INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- ============================================================================
-- TELEMETRY DATA
-- ============================================================================

-- Device metrics (battery, voltage, etc.)
CREATE TABLE device_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    
    -- Battery and power
    battery_level INTEGER,        -- 0-100 percentage, >100 means powered
    voltage REAL,                 -- Voltage measurement
    
    -- Network utilization
    channel_utilization REAL,    -- Channel usage percentage
    air_util_tx REAL,            -- Transmit airtime percentage
    
    -- System metrics
    uptime_seconds INTEGER,       -- Device uptime
    
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Environment metrics (sensors)
CREATE TABLE environment_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    
    -- Weather data
    temperature REAL,
    relative_humidity REAL,
    barometric_pressure REAL,
    wind_direction INTEGER,       -- Degrees
    wind_speed REAL,             -- m/s
    wind_gust REAL,
    wind_lull REAL,
    rainfall_1h REAL,            -- mm
    rainfall_24h REAL,           -- mm
    
    -- Air quality
    gas_resistance REAL,         -- MOhm
    iaq INTEGER,                 -- Indoor Air Quality 0-500
    
    -- Light sensors
    lux REAL,                    -- Ambient light
    white_lux REAL,
    ir_lux REAL,
    uv_lux REAL,
    
    -- Other sensors
    distance REAL,               -- mm (e.g., water level)
    weight REAL,                 -- kg
    soil_moisture INTEGER,       -- Percentage
    soil_temperature REAL,       -- °C
    radiation REAL,              -- µR/h
    
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Power metrics (multi-channel)
CREATE TABLE power_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    
    -- Up to 8 channels
    ch1_voltage REAL, ch1_current REAL,
    ch2_voltage REAL, ch2_current REAL,
    ch3_voltage REAL, ch3_current REAL,
    ch4_voltage REAL, ch4_current REAL,
    ch5_voltage REAL, ch5_current REAL,
    ch6_voltage REAL, ch6_current REAL,
    ch7_voltage REAL, ch7_current REAL,
    ch8_voltage REAL, ch8_current REAL,
    
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- ============================================================================
-- MESSAGES & PACKETS
-- ============================================================================

-- All mesh packets for network analysis
CREATE TABLE mesh_packets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    
    -- Packet header
    packet_id INTEGER NOT NULL,   -- Meshtastic packet ID (fixed32)
    from_node INTEGER NOT NULL,   -- Source node ID
    to_node INTEGER NOT NULL,     -- Destination (0 = broadcast)
    channel INTEGER DEFAULT 0,
    
    -- Routing information  
    hop_limit INTEGER,            -- TTL
    hop_start INTEGER,            -- Original hop count
    next_hop INTEGER,             -- Next hop in route
    relay_node INTEGER,           -- Relay node ID
    
    -- RF metrics
    rx_time INTEGER,              -- Receive timestamp
    rx_rssi INTEGER,              -- RSSI when received
    rx_snr REAL,                  -- SNR when received
    
    -- Packet metadata
    want_ack BOOLEAN DEFAULT 0,
    via_mqtt BOOLEAN DEFAULT 0,
    is_encrypted BOOLEAN DEFAULT 0,
    priority INTEGER DEFAULT 0,   -- Message priority
    portnum INTEGER,              -- Application port number
    
    -- Payload (if decrypted)
    payload_size INTEGER,
    payload_hash TEXT,            -- SHA256 of payload for dedup
    
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Text messages
CREATE TABLE text_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    packet_id INTEGER NOT NULL,  -- Links to mesh_packets
    session_id INTEGER NOT NULL,
    
    from_node INTEGER NOT NULL,
    to_node INTEGER NOT NULL,    -- 0 for broadcast
    channel INTEGER,
    
    message_text TEXT NOT NULL,
    
    -- Message metadata
    is_broadcast BOOLEAN DEFAULT 0,
    is_direct BOOLEAN DEFAULT 0,
    
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (packet_id) REFERENCES mesh_packets(id) ON DELETE CASCADE
);

-- Route tracking for network topology
CREATE TABLE packet_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    packet_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    
    hop_number INTEGER NOT NULL,  -- 0 = source, 1 = first hop, etc.
    node_id INTEGER NOT NULL,     -- Node at this hop
    rssi INTEGER,                 -- RSSI at this hop
    snr REAL,                     -- SNR at this hop
    
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (packet_id) REFERENCES mesh_packets(id) ON DELETE CASCADE
);

-- ============================================================================
-- NETWORK TOPOLOGY
-- ============================================================================

-- Node connections and link quality
CREATE TABLE node_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    
    from_node INTEGER NOT NULL,
    to_node INTEGER NOT NULL,
    
    -- Link quality metrics
    packet_count INTEGER DEFAULT 1,
    success_rate REAL,            -- Percentage of successful packets
    avg_rssi REAL,
    avg_snr REAL,
    avg_hop_count REAL,
    
    -- Link state
    is_direct BOOLEAN DEFAULT 0,  -- Direct connection vs multi-hop
    last_seen INTEGER,            -- Last packet on this link
    
    first_seen INTEGER NOT NULL DEFAULT (unixepoch()),
    last_updated INTEGER NOT NULL DEFAULT (unixepoch()),
    
    PRIMARY KEY (session_id, from_node, to_node),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Neighbor information (direct connections)
CREATE TABLE node_neighbors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    
    neighbor_id INTEGER NOT NULL,
    snr REAL,                     -- Signal quality to neighbor
    
    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Session queries
CREATE INDEX idx_sessions_active ON sessions(is_active) WHERE is_active = 1;

-- Node queries  
CREATE INDEX idx_nodes_session ON nodes(session_id);
CREATE INDEX idx_nodes_last_heard ON nodes(last_heard DESC);
CREATE INDEX idx_nodes_active ON nodes(session_id, last_heard) WHERE last_heard > (unixepoch() - 3600);

-- Position queries
CREATE INDEX idx_position_history_node_time ON position_history(node_id, timestamp DESC);
CREATE INDEX idx_position_history_session_time ON position_history(session_id, timestamp DESC);
CREATE INDEX idx_position_current_session ON node_positions(session_id);

-- Telemetry queries
CREATE INDEX idx_device_metrics_node_time ON device_metrics(node_id, timestamp DESC);
CREATE INDEX idx_environment_metrics_node_time ON environment_metrics(node_id, timestamp DESC);
CREATE INDEX idx_power_metrics_node_time ON power_metrics(node_id, timestamp DESC);

-- Message and packet queries
CREATE INDEX idx_mesh_packets_session_time ON mesh_packets(session_id, timestamp DESC);
CREATE INDEX idx_mesh_packets_from_time ON mesh_packets(from_node, timestamp DESC);
CREATE INDEX idx_mesh_packets_to_time ON mesh_packets(to_node, timestamp DESC);
CREATE INDEX idx_mesh_packets_hash ON mesh_packets(payload_hash);

CREATE INDEX idx_text_messages_session_time ON text_messages(session_id, timestamp DESC);
CREATE INDEX idx_text_messages_from_time ON text_messages(from_node, timestamp DESC);
CREATE INDEX idx_text_messages_broadcast ON text_messages(session_id, is_broadcast, timestamp DESC);

-- Network topology queries
CREATE INDEX idx_node_links_session ON node_links(session_id);
CREATE INDEX idx_node_links_from ON node_links(from_node, last_updated DESC);
CREATE INDEX idx_node_links_to ON node_links(to_node, last_updated DESC);
CREATE INDEX idx_node_links_direct ON node_links(session_id, is_direct) WHERE is_direct = 1;

CREATE INDEX idx_packet_routes_packet ON packet_routes(packet_id, hop_number);
CREATE INDEX idx_neighbors_node ON node_neighbors(node_id, session_id);

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert hardware models
INSERT INTO hardware_models (id, name, display_name) VALUES
(0, 'UNSET', 'Unset'),
(1, 'TLORA_V2', 'T-LoRa V2'),
(2, 'TLORA_V1', 'T-LoRa V1'), 
(3, 'TLORA_V2_1_1P6', 'T-LoRa V2.1-1.6'),
(4, 'TBEAM', 'T-Beam'),
(5, 'HELTEC_V2_0', 'Heltec V2.0'),
(6, 'TBEAM_V0P7', 'T-Beam V0.7'),
(7, 'T_ECHO', 'T-Echo'),
(8, 'TLORA_V2_1_1P8', 'T-LoRa V2.1-1.8'),
(9, 'TLORA_V1_1P3', 'T-LoRa V1.1-1.3'),
(10, 'RAK4631', 'RAK4631'),
(11, 'HELTEC_V2_1', 'Heltec V2.1'),
(12, 'HELTEC_V1', 'Heltec V1'),
(13, 'LILYGO_TBEAM_S3_CORE', 'LilyGO T-Beam S3 Core'),
(14, 'RAK11200', 'RAK11200'),
(15, 'NANO_G1', 'Nano G1'),
(16, 'TLORA_V2_1_1P6_915', 'T-LoRa V2.1-1.6 915MHz'),
(17, 'NANO_G1_EXPLORER', 'Nano G1 Explorer'),
(18, 'NANO_G2_ULTRA', 'Nano G2 Ultra'),
(25, 'PORTDUINO', 'Portduino'),
(26, 'ANDROID_SIM', 'Android Simulator'),
(39, 'DIY_V1', 'DIY V1'),
(40, 'NRF52840DK', 'nRF52840-DK'),
(41, 'PPR', 'PPR'),
(42, 'GENIEBLOCKS', 'GenieBlocks'),
(43, 'NRF52_UNKNOWN', 'nRF52 Unknown'),
(44, 'PORTDUINO_LINUX_NATIVE', 'Portduino Linux Native'),
(255, 'PRIVATE_HW', 'Private Hardware');

-- Insert node roles  
INSERT INTO node_roles (id, name, description) VALUES
(0, 'CLIENT', 'Standard mesh client'),
(1, 'CLIENT_MUTE', 'Client that does not forward packets'),
(2, 'ROUTER', 'Dedicated router node'),
(3, 'ROUTER_CLIENT', 'Router that also acts as client');

-- Create initial active session
INSERT INTO sessions (name, start_time, is_active, description) VALUES
('Default Session', unixepoch(), 1, 'Initial active session');

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active session view
CREATE VIEW active_session AS
SELECT * FROM sessions WHERE is_active = 1;

-- Current nodes with full details
CREATE VIEW current_nodes AS
SELECT 
    n.*,
    hm.display_name as hardware_model_name,
    nr.name as role_name,
    p.latitude,
    p.longitude,
    p.altitude,
    dm.battery_level,
    dm.voltage,
    dm.channel_utilization,
    CASE 
        WHEN n.last_heard > (unixepoch() - 300) THEN 'online'
        WHEN n.last_heard > (unixepoch() - 3600) THEN 'recent'  
        ELSE 'offline'
    END as status
FROM nodes n
JOIN active_session s ON n.session_id = s.id
LEFT JOIN hardware_models hm ON n.hardware_model_id = hm.id
LEFT JOIN node_roles nr ON n.role_id = nr.id
LEFT JOIN node_positions p ON n.id = p.node_id AND n.session_id = p.session_id
LEFT JOIN (
    SELECT DISTINCT node_id, session_id, 
           first_value(battery_level) OVER (PARTITION BY node_id ORDER BY timestamp DESC) as battery_level,
           first_value(voltage) OVER (PARTITION BY node_id ORDER BY timestamp DESC) as voltage,
           first_value(channel_utilization) OVER (PARTITION BY node_id ORDER BY timestamp DESC) as channel_utilization
    FROM device_metrics 
    WHERE session_id = (SELECT id FROM active_session)
) dm ON n.id = dm.node_id AND n.session_id = dm.session_id;

-- Network topology view
CREATE VIEW network_topology AS
SELECT 
    nl.*,
    n1.short_name as from_name,
    n2.short_name as to_name,
    CASE 
        WHEN nl.last_seen > (unixepoch() - 300) THEN 'active'
        WHEN nl.last_seen > (unixepoch() - 3600) THEN 'recent'
        ELSE 'stale'
    END as link_status
FROM node_links nl
JOIN active_session s ON nl.session_id = s.id
LEFT JOIN nodes n1 ON nl.from_node = n1.id AND nl.session_id = n1.session_id
LEFT JOIN nodes n2 ON nl.to_node = n2.id AND nl.session_id = n2.session_id;

-- Recent messages view
CREATE VIEW recent_messages AS
SELECT 
    tm.*,
    n1.short_name as from_name,
    n2.short_name as to_name,
    CASE WHEN tm.to_node = 0 THEN 'broadcast' ELSE 'direct' END as message_type
FROM text_messages tm
JOIN active_session s ON tm.session_id = s.id
LEFT JOIN nodes n1 ON tm.from_node = n1.id AND tm.session_id = n1.session_id
LEFT JOIN nodes n2 ON tm.to_node = n2.id AND tm.session_id = n2.session_id
ORDER BY tm.timestamp DESC;

COMMIT;