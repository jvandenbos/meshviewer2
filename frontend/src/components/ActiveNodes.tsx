import React from 'react';
import { NodeInfo } from '../types';
import { Battery, Radio, Router, WifiOff, Wifi } from 'lucide-react';

interface ActiveNodesProps {
  nodes: NodeInfo[];
  selectedNodeId: string | null;
  onNodeSelect: (node: NodeInfo) => void;
}

const ActiveNodes: React.FC<ActiveNodesProps> = ({ 
  nodes, 
  selectedNodeId, 
  onNodeSelect 
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

  // Sort nodes by last heard (most recent first)
  const sortedNodes = [...nodes].sort((a, b) => 
    new Date(b.last_heard).getTime() - new Date(a.last_heard).getTime()
  );

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
            className={`p-3 border-b border-gray-700 cursor-pointer transition-colors hover:bg-gray-700 ${
              selectedNodeId === node.id ? 'bg-gray-700' : ''
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-white">{node.short_name}</h3>
                  {getSignalIcon(node.signal_quality)}
                  {node.rssi && (
                    <span className="text-xs text-gray-400">{node.rssi}dBm</span>
                  )}
                </div>
                
                {node.long_name && (
                  <p className="text-xs text-gray-400 mt-1">{node.long_name}</p>
                )}
                
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                  {node.battery_level !== undefined && (
                    <div className="flex items-center gap-1">
                      <Battery className={`w-3 h-3 ${getBatteryColor(node.battery_level)}`} />
                      <span>{node.battery_level}%</span>
                    </div>
                  )}
                  
                  {node.hop_count > 0 && (
                    <div className="flex items-center gap-1">
                      <Router className="w-3 h-3" />
                      <span>{node.hop_count} hops</span>
                    </div>
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