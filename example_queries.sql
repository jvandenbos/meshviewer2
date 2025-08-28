-- ============================================================================
-- EXAMPLE QUERIES FOR MESHTASTIC VISUALIZER
-- Common query patterns for real-time visualization and analysis
-- ============================================================================

-- ============================================================================
-- REAL-TIME DASHBOARD QUERIES
-- ============================================================================

-- 1. Get all active nodes (last seen within 5 minutes)
SELECT 
    id,
    short_name,
    long_name,
    hardware_model_name,
    role_name,
    latitude,
    longitude,
    battery_level,
    voltage,
    snr,
    rssi,
    hops_away,
    status,
    (unixepoch() - last_heard) as seconds_ago
FROM current_nodes 
WHERE last_heard > (unixepoch() - 300)
ORDER BY last_heard DESC;

-- 2. Get node count by status
SELECT 
    status,
    COUNT(*) as count
FROM current_nodes 
GROUP BY status;

-- 3. Get network statistics
SELECT 
    COUNT(DISTINCT id) as total_nodes,
    COUNT(CASE WHEN last_heard > (unixepoch() - 300) THEN 1 END) as active_nodes,
    COUNT(CASE WHEN battery_level IS NOT NULL AND battery_level <= 20 THEN 1 END) as low_battery_nodes,
    AVG(CASE WHEN battery_level IS NOT NULL AND battery_level <= 100 THEN battery_level END) as avg_battery,
    MAX(hops_away) as max_hops,
    AVG(snr) as avg_snr
FROM current_nodes;

-- ============================================================================
-- MESSAGE FLOW VISUALIZATION  
-- ============================================================================

-- 4. Recent messages (last hour) with sender/receiver details
SELECT 
    from_name,
    to_name,
    message_text,
    message_type,
    datetime(timestamp, 'unixepoch', 'localtime') as sent_time,
    (unixepoch() - timestamp) as seconds_ago
FROM recent_messages 
WHERE timestamp > (unixepoch() - 3600)
ORDER BY timestamp DESC 
LIMIT 50;

-- 5. Message activity by hour (last 24 hours)
SELECT 
    datetime(timestamp - (timestamp % 3600), 'unixepoch', 'localtime') as hour,
    COUNT(*) as message_count,
    COUNT(DISTINCT from_node) as active_senders,
    COUNT(CASE WHEN is_broadcast = 1 THEN 1 END) as broadcast_count
FROM text_messages tm
JOIN active_session s ON tm.session_id = s.id
WHERE timestamp > (unixepoch() - 86400)
GROUP BY (timestamp / 3600)
ORDER BY hour DESC;

-- 6. Most active nodes (by message count)
SELECT 
    n.short_name,
    n.long_name,
    COUNT(tm.id) as message_count,
    MAX(tm.timestamp) as last_message_time,
    datetime(MAX(tm.timestamp), 'unixepoch', 'localtime') as last_message
FROM nodes n
JOIN active_session s ON n.session_id = s.id
LEFT JOIN text_messages tm ON n.id = tm.from_node AND n.session_id = tm.session_id
WHERE tm.timestamp > (unixepoch() - 86400) -- Last 24 hours
GROUP BY n.id, n.short_name, n.long_name
ORDER BY message_count DESC
LIMIT 10;

-- ============================================================================
-- NETWORK TOPOLOGY ANALYSIS
-- ============================================================================

-- 7. Active network links with signal quality
SELECT 
    from_name,
    to_name,
    packet_count,
    success_rate,
    avg_rssi,
    avg_snr,
    avg_hop_count,
    is_direct,
    link_status,
    datetime(last_seen, 'unixepoch', 'localtime') as last_seen_time
FROM network_topology 
WHERE last_seen > (unixepoch() - 3600) -- Last hour
ORDER BY packet_count DESC;

-- 8. Find potential gateway/router nodes (high connectivity)
SELECT 
    n.id,
    n.short_name,
    n.role_name,
    COUNT(DISTINCT nl1.to_node) as outgoing_links,
    COUNT(DISTINCT nl2.from_node) as incoming_links,
    COUNT(DISTINCT nl1.to_node) + COUNT(DISTINCT nl2.from_node) as total_links,
    AVG(CASE WHEN nl1.avg_rssi IS NOT NULL THEN nl1.avg_rssi END) as avg_outgoing_rssi
FROM current_nodes n
LEFT JOIN node_links nl1 ON n.id = nl1.from_node AND n.session_id = nl1.session_id
    AND nl1.last_seen > (unixepoch() - 3600)
LEFT JOIN node_links nl2 ON n.id = nl2.to_node AND n.session_id = nl2.session_id  
    AND nl2.last_seen > (unixepoch() - 3600)
GROUP BY n.id, n.short_name, n.role_name
HAVING total_links > 2
ORDER BY total_links DESC;

-- 9. Routing path analysis (find multi-hop routes)
SELECT 
    pr.packet_id,
    mp.from_node,
    mp.to_node,
    GROUP_CONCAT(pr.node_id, ' -> ') as route_path,
    AVG(pr.rssi) as avg_route_rssi,
    COUNT(*) as hop_count
FROM packet_routes pr
JOIN mesh_packets mp ON pr.packet_id = mp.id
JOIN active_session s ON pr.session_id = s.id
WHERE pr.timestamp > (unixepoch() - 3600)
GROUP BY pr.packet_id
HAVING hop_count > 1
ORDER BY pr.packet_id DESC
LIMIT 20;

-- ============================================================================
-- GEOGRAPHIC VISUALIZATION
-- ============================================================================

-- 10. Nodes with GPS positions for mapping
SELECT 
    id,
    short_name,
    latitude,
    longitude,  
    altitude,
    battery_level,
    status,
    datetime(last_heard, 'unixepoch', 'localtime') as last_heard_time,
    CASE 
        WHEN status = 'online' THEN '#00FF00'
        WHEN status = 'recent' THEN '#FFA500'  
        ELSE '#FF0000'
    END as marker_color
FROM current_nodes 
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
ORDER BY last_heard DESC;

-- 11. Position history for node movement tracking  
SELECT 
    ph.node_id,
    n.short_name,
    ph.latitude,
    ph.longitude,
    ph.altitude,
    datetime(ph.position_time, 'unixepoch', 'localtime') as position_time,
    ph.timestamp
FROM position_history ph
JOIN nodes n ON ph.node_id = n.id AND ph.session_id = n.session_id
JOIN active_session s ON ph.session_id = s.id
WHERE ph.timestamp > (unixepoch() - 86400) -- Last 24 hours
  AND ph.node_id = ? -- Parameter for specific node
ORDER BY ph.timestamp DESC;

-- 12. Calculate distance between nodes (requires SQLite with math functions)
SELECT 
    n1.short_name as node1,
    n2.short_name as node2,
    n1.latitude as lat1,
    n1.longitude as lon1,
    n2.latitude as lat2,
    n2.longitude as lon2,
    -- Haversine distance formula (approximate)
    ROUND(
        6371 * acos(
            cos(radians(n1.latitude)) * cos(radians(n2.latitude)) * 
            cos(radians(n2.longitude) - radians(n1.longitude)) + 
            sin(radians(n1.latitude)) * sin(radians(n2.latitude))
        ), 2
    ) as distance_km
FROM current_nodes n1
CROSS JOIN current_nodes n2
WHERE n1.id < n2.id  -- Avoid duplicates
  AND n1.latitude IS NOT NULL AND n1.longitude IS NOT NULL
  AND n2.latitude IS NOT NULL AND n2.longitude IS NOT NULL
ORDER BY distance_km;

-- ============================================================================
-- TELEMETRY MONITORING
-- ============================================================================

-- 13. Battery levels and power status
SELECT 
    n.short_name,
    dm.battery_level,
    dm.voltage,
    dm.channel_utilization,
    dm.air_util_tx,
    dm.uptime_seconds,
    datetime(dm.timestamp, 'unixepoch', 'localtime') as reading_time,
    CASE 
        WHEN dm.battery_level > 100 THEN 'External Power'
        WHEN dm.battery_level > 50 THEN 'Good'
        WHEN dm.battery_level > 20 THEN 'Low'
        WHEN dm.battery_level IS NOT NULL THEN 'Critical'
        ELSE 'Unknown'
    END as battery_status
FROM nodes n
JOIN active_session s ON n.session_id = s.id
LEFT JOIN device_metrics dm ON n.id = dm.node_id AND n.session_id = dm.session_id
WHERE dm.timestamp = (
    SELECT MAX(timestamp) 
    FROM device_metrics dm2 
    WHERE dm2.node_id = n.id AND dm2.session_id = n.session_id
)
ORDER BY dm.battery_level ASC NULLS LAST;

-- 14. Environmental sensor readings (last 24 hours)
SELECT 
    n.short_name,
    em.temperature,
    em.relative_humidity,
    em.barometric_pressure,
    em.lux,
    em.wind_speed,
    em.wind_direction,
    datetime(em.timestamp, 'unixepoch', 'localtime') as reading_time
FROM environment_metrics em
JOIN nodes n ON em.node_id = n.id AND em.session_id = n.session_id
JOIN active_session s ON em.session_id = s.id
WHERE em.timestamp > (unixepoch() - 86400)
ORDER BY em.timestamp DESC;

-- 15. Node uptime tracking
SELECT 
    n.short_name,
    dm.uptime_seconds,
    ROUND(dm.uptime_seconds / 3600.0, 1) as uptime_hours,
    ROUND(dm.uptime_seconds / 86400.0, 1) as uptime_days,
    datetime(dm.timestamp, 'unixepoch', 'localtime') as reading_time
FROM device_metrics dm
JOIN nodes n ON dm.node_id = n.id AND dm.session_id = n.session_id  
JOIN active_session s ON dm.session_id = s.id
WHERE dm.uptime_seconds IS NOT NULL
  AND dm.timestamp = (
    SELECT MAX(timestamp) 
    FROM device_metrics dm2 
    WHERE dm2.node_id = dm.node_id AND dm2.session_id = dm.session_id
)
ORDER BY dm.uptime_seconds DESC;

-- ============================================================================
-- PERFORMANCE AND MONITORING
-- ============================================================================

-- 16. Signal quality analysis
SELECT 
    percentile_90,
    percentile_50,
    avg_snr,
    min_snr,
    max_snr,
    node_count
FROM (
    SELECT 
        ROUND(AVG(snr), 2) as avg_snr,
        ROUND(MIN(snr), 2) as min_snr,
        ROUND(MAX(snr), 2) as max_snr,
        COUNT(*) as node_count,
        -- Approximate percentiles using NTILE
        ROUND(AVG(CASE WHEN snr_rank <= 0.5 THEN snr END), 2) as percentile_50,
        ROUND(AVG(CASE WHEN snr_rank <= 0.9 THEN snr END), 2) as percentile_90
    FROM (
        SELECT 
            snr,
            NTILE(100) OVER (ORDER BY snr) / 100.0 as snr_rank
        FROM current_nodes 
        WHERE snr IS NOT NULL
    )
);

-- 17. Packet loss analysis by link
SELECT 
    from_name,
    to_name,
    packet_count,
    success_rate,
    100 - success_rate as loss_rate,
    avg_rssi,
    avg_snr,
    datetime(last_seen, 'unixepoch', 'localtime') as last_activity
FROM network_topology 
WHERE packet_count >= 5  -- Only links with reasonable sample size
ORDER BY success_rate ASC;

-- 18. Network health summary
SELECT 
    'Total Nodes' as metric,
    COUNT(*) as value,
    '' as unit
FROM current_nodes
UNION ALL
SELECT 
    'Active Nodes (5m)',
    COUNT(CASE WHEN last_heard > (unixepoch() - 300) THEN 1 END),
    ''
FROM current_nodes
UNION ALL  
SELECT 
    'Avg SNR',
    ROUND(AVG(snr), 2),
    'dB'
FROM current_nodes WHERE snr IS NOT NULL
UNION ALL
SELECT 
    'Avg Battery',
    ROUND(AVG(CASE WHEN battery_level <= 100 THEN battery_level END), 1),
    '%'
FROM current_nodes WHERE battery_level IS NOT NULL
UNION ALL
SELECT 
    'Messages (24h)',
    COUNT(*),
    ''
FROM text_messages tm
JOIN active_session s ON tm.session_id = s.id  
WHERE timestamp > (unixepoch() - 86400)
UNION ALL
SELECT 
    'Active Links (1h)',
    COUNT(*),
    ''
FROM network_topology 
WHERE last_seen > (unixepoch() - 3600);

-- ============================================================================
-- DATA CLEANUP AND ARCHIVAL
-- ============================================================================

-- 19. Archive old session data  
-- (Run this periodically to move current session to historical tables)
/*
BEGIN TRANSACTION;

-- Create new session  
INSERT INTO sessions (name, start_time, is_active, description) 
VALUES ('Session ' || datetime('now'), unixepoch(), 0, 'Archived session');

SET @old_session_id = last_insert_rowid();

-- Update current session to inactive
UPDATE sessions SET is_active = 0, end_time = unixepoch() 
WHERE is_active = 1;

-- Move nodes to history
INSERT INTO nodes_history (node_id, session_id, short_name, long_name, hardware_model, role, snr, rssi, hops_away, channel, via_mqtt, timestamp)
SELECT 
    n.id, n.session_id, n.short_name, n.long_name, hm.name, nr.name, n.snr, n.rssi, n.hops_away, n.channel, n.via_mqtt, n.last_updated
FROM nodes n
LEFT JOIN hardware_models hm ON n.hardware_model_id = hm.id  
LEFT JOIN node_roles nr ON n.role_id = nr.id
WHERE n.session_id = @old_session_id;

-- Create new active session
INSERT INTO sessions (name, start_time, is_active, description)
VALUES ('New Active Session', unixepoch(), 1, 'Current active session');

COMMIT;
*/

-- 20. Cleanup old data (run periodically)
-- Delete data older than 30 days for inactive sessions
/*
DELETE FROM mesh_packets 
WHERE session_id IN (
    SELECT id FROM sessions 
    WHERE is_active = 0 AND end_time < (unixepoch() - 2592000)
);

DELETE FROM position_history 
WHERE timestamp < (unixepoch() - 2592000);

DELETE FROM device_metrics 
WHERE timestamp < (unixepoch() - 2592000);

DELETE FROM environment_metrics 
WHERE timestamp < (unixepoch() - 2592000);
*/

-- 21. Database maintenance
-- Analyze tables for query optimization
ANALYZE;

-- Vacuum to reclaim space (run periodically)  
-- VACUUM;

-- ============================================================================
-- DEBUGGING AND DIAGNOSTICS
-- ============================================================================

-- 22. Find duplicate packets (by payload hash)
SELECT 
    payload_hash,
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(DISTINCT from_node) as source_nodes
FROM mesh_packets 
WHERE payload_hash IS NOT NULL
GROUP BY payload_hash
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- 23. Node activity timeline (for debugging connectivity issues)
SELECT 
    node_id,
    short_name,
    datetime(timestamp, 'unixepoch', 'localtime') as activity_time,
    'position' as activity_type
FROM position_history ph
JOIN nodes n ON ph.node_id = n.id AND ph.session_id = n.session_id
WHERE ph.timestamp > (unixepoch() - 86400)
  AND node_id = ? -- Parameter

UNION ALL

SELECT 
    node_id,
    short_name,
    datetime(timestamp, 'unixepoch', 'localtime'),
    'device_metrics'
FROM device_metrics dm
JOIN nodes n ON dm.node_id = n.id AND dm.session_id = n.session_id
WHERE dm.timestamp > (unixepoch() - 86400)
  AND node_id = ?

UNION ALL

SELECT 
    from_node as node_id,
    short_name, 
    datetime(timestamp, 'unixepoch', 'localtime'),
    'message_sent'
FROM text_messages tm
JOIN nodes n ON tm.from_node = n.id AND tm.session_id = n.session_id
WHERE tm.timestamp > (unixepoch() - 86400)
  AND from_node = ?

ORDER BY activity_time DESC;

-- 24. Check database integrity and size
SELECT 
    'Database Size' as info,
    ROUND((page_count * page_size) / 1024.0 / 1024.0, 2) as size_mb
FROM pragma_page_count(), pragma_page_size()
UNION ALL
SELECT 
    'Table Count',
    COUNT(*) 
FROM sqlite_master WHERE type = 'table'
UNION ALL
SELECT 
    'Index Count',
    COUNT(*)
FROM sqlite_master WHERE type = 'index';