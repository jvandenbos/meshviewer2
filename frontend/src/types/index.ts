export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface NodeInfo {
  id: string;
  short_name: string;
  long_name?: string;
  hardware_model?: string;
  role?: string;
  battery_level?: number;
  voltage?: number;
  rssi?: number;
  snr?: number;
  hop_count: number;
  latitude?: number;
  longitude?: number;
  altitude?: number;
  last_heard: string;
  is_online: boolean;
  signal_quality?: 'excellent' | 'good' | 'weak' | 'poor';
}

export interface TextMessage {
  from_id: string;
  from_name: string;
  to_id: string;
  to_name: string;
  message: string;
  timestamp: string;
  rssi?: number;
  snr?: number;
  hop_count: number;
}

export interface NetworkLink {
  from_id: string;
  to_id: string;
  rssi?: number;
  snr?: number;
  success_rate: number;
  last_seen: string;
  is_direct: boolean;
}

export interface Session {
  id: number;
  started_at: string;
  ended_at?: string;
  is_active: boolean;
  node_count: number;
  message_count: number;
}