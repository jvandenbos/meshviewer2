import React from 'react';
import { NodeInfo } from '../types';
import { Battery, Radio, Router, WifiOff, Wifi } from 'lucide-react';
import SignalStrengthGauge from './SignalStrengthGauge';

interface ActiveNodesProps {
  nodes: NodeInfo[];
  selectedNodeId: string | null;
  onNodeSelect: (node: NodeInfo) => void;
  localNodeId?: string;
}

const ActiveNodes: React.FC<ActiveNodesProps> = ({ 
  nodes, 
  selectedNodeId, 
  onNodeSelect,
  localNodeId = '1109198442'  // Default to known local node
}) => {
  const getSignalIcon = (quality?: string) => {
    switch (quality) {
      case 'excellent':
        return <Wifi className="w-4 h-4 text-green-500" />;
      case 'good':
        return <Wifi className="w-4 h-4 text-yellow-500" />;
      case 'weak':
        return <Radio className="w-4 h-4 text-orange-500" />;
      case 'poor':
        return <WifiOff className="w-4 h-4 text-red-500" />;
      default:
        return <Radio className="w-4 h-4 text-gray-500" />;
    }
  };

  const getBatteryColor = (level?: number) => {
    if (!level) return 'text-gray-500';
    if (level > 75) return 'text-green-500';
    if (level > 50) return 'text-yellow-500';
    if (level > 25) return 'text-orange-500';
    return 'text-red-500';
  };

  const formatLastHeard = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  // Sort nodes: My node first, then direct (1 hop), then ascending by hop count
  const sortedNodes = [...nodes].sort((a, b) => {
    // My node always first (only by ID match)
    const aIsLocal = a.id === localNodeId;
    const bIsLocal = b.id === localNodeId;
    
    if (aIsLocal && !bIsLocal) return -1;
    if (!aIsLocal && bIsLocal) return 1;
    if (aIsLocal && bIsLocal) return 0; // Both local (shouldn't happen)
    
    // Get hop counts, treating undefined/null as very high number
    const aHops = a.hop_count ?? 999;
    const bHops = b.hop_count ?? 999;
    
    // Direct connections (1 hop) come before everything else
    if (aHops === 1 && bHops !== 1) return -1;
    if (aHops !== 1 && bHops === 1) return 1;
    
    // Sort by hop count (ascending: 2, 3, 4...)
    if (aHops !== bHops) {
      return aHops - bHops;
    }
    
    // If same hop count, sort by last heard (most recent first)
    return new Date(b.last_heard).getTime() - new Date(a.last_heard).getTime();
  });

  return (
    <div className="w-80 bg-gray-800 border-l border-gray-700 overflow-hidden flex flex-col">
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Active Nodes</h2>
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span>{nodes.filter(n => n.is_online).length} Live</span>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {sortedNodes.map((node) => (
          <div
            key={node.id}
            onClick={() => onNodeSelect(node)}
            className={`p-3 border-b border-gray-700 cursor-pointer transition-colors hover:bg-gray-700 relative ${
              selectedNodeId === node.id ? 'bg-gray-700' : ''
            }`}
          >
            {/* Hop count badge in upper right */}
            {(node.id === localNodeId || (node.hop_count !== undefined && node.hop_count < 999)) && (
              <div className="absolute top-2 right-2">
                <span className={`px-2 py-1 text-xs font-bold rounded ${
                  node.id === localNodeId 
                    ? 'bg-green-600 text-white' 
                    : node.hop_count === 1 
                    ? 'bg-blue-600 text-white' 
                    : node.hop_count === 2
                    ? 'bg-yellow-600 text-white'
                    : node.hop_count && node.hop_count >= 3
                    ? 'bg-orange-600 text-white'
                    : 'bg-gray-600 text-white'
                }`}>
                  {node.id === localNodeId ? 'LOCAL' : 
                   node.hop_count === 1 ? 'DIRECT' : 
                   node.hop_count && node.hop_count < 999 ? `${node.hop_count} HOPS` : 
                   'UNKNOWN'}
                </span>
              </div>
            )}
            
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-white">
                    {node.short_name}
                    {node.id === localNodeId && (
                      <span className="ml-2 text-xs bg-cyan-600 text-white px-1.5 py-0.5 rounded">MY NODE</span>
                    )}
                  </h3>
                  <SignalStrengthGauge 
                    rssi={node.rssi} 
                    quality={node.signal_quality} 
                    compact={true} 
                  />
                </div>
                
                {node.long_name && (
                  <p className="text-xs text-gray-400 mt-1">{node.long_name}</p>
                )}
                
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                  {node.battery_level !== undefined && node.battery_level !== null && (
                    <div className="flex items-center gap-1">
                      <Battery className={`w-3 h-3 ${getBatteryColor(node.battery_level)}`} />
                      <span>{node.battery_level}%</span>
                    </div>
                  )}
                  
                  {node.voltage !== undefined && node.voltage !== null && (
                    <span>{node.voltage.toFixed(2)}V</span>
                  )}
                  
                  {node.snr !== undefined && node.snr !== null && (
                    <span>SNR: {node.snr.toFixed(1)}</span>
                  )}
                  
                  <span className="text-gray-600">
                    {formatLastHeard(node.last_heard)}
                  </span>
                </div>
              </div>
            </div>
            
            {node.hardware_model && (
              <div className="mt-2 text-xs text-gray-500">
                {node.hardware_model} • {node.role || 'CLIENT'}
              </div>
            )}
          </div>
        ))}
        
        {nodes.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            <Radio className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No nodes discovered yet</p>
            <p className="text-xs mt-1">Waiting for network activity...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ActiveNodes;