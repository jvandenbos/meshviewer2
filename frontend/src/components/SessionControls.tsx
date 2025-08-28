import React from 'react';
import { PlayCircle, StopCircle, RefreshCw, Activity, Users, MessageSquare } from 'lucide-react';
import { Session } from '../types';

interface SessionControlsProps {
  session: Session | null;
  isConnected: boolean;
  nodeCount: number;
  messageCount: number;
  onNewSession: () => void;
  onConnect: () => void;
  onDisconnect: () => void;
}

const SessionControls: React.FC<SessionControlsProps> = ({
  session,
  isConnected,
  nodeCount,
  messageCount,
  onNewSession,
  onConnect,
  onDisconnect
}) => {
  const formatDuration = (startTime: string) => {
    const start = new Date(startTime);
    const now = new Date();
    const diff = Math.floor((now.getTime() - start.getTime()) / 1000);
    
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  };

  return (
    <div className="h-16 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-6">
      <div className="flex items-center gap-6">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Activity className="w-6 h-6 text-cyan-400" />
          Meshtastic Visualizer
        </h1>
        
        <div className="flex items-center gap-2">
          {isConnected ? (
            <button
              onClick={onDisconnect}
              className="flex items-center gap-2 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors text-sm"
            >
              <StopCircle className="w-4 h-4" />
              Disconnect
            </button>
          ) : (
            <button
              onClick={onConnect}
              className="flex items-center gap-2 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors text-sm"
            >
              <PlayCircle className="w-4 h-4" />
              Connect
            </button>
          )}
          
          <button
            onClick={onNewSession}
            className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors text-sm"
          >
            <RefreshCw className="w-4 h-4" />
            New Session
          </button>
        </div>
      </div>
      
      <div className="flex items-center gap-6">
        {session && (
          <>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-400">Session Time:</span>
              <span className="text-white font-medium">
                {formatDuration(session.started_at)}
              </span>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-cyan-400" />
                <span className="text-white font-medium">{nodeCount}</span>
                <span className="text-gray-400 text-sm">nodes</span>
              </div>
              
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-purple-400" />
                <span className="text-white font-medium">{messageCount}</span>
                <span className="text-gray-400 text-sm">messages</span>
              </div>
            </div>
          </>
        )}
        
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-400">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default SessionControls;