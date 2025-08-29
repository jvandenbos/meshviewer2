import React, { useEffect, useRef } from 'react';
import { MessageSquare, Radio, MapPin, Battery, Link2 } from 'lucide-react';

interface Event {
  id: string;
  type: 'message' | 'node_discovered' | 'position' | 'telemetry' | 'connection';
  text: string;
  timestamp: Date;
  color?: string;
}

interface EventTickerProps {
  events: Event[];
  maxEvents?: number;
}

const EventTicker: React.FC<EventTickerProps> = ({ events, maxEvents = 100 }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    // Auto-scroll to latest event
    if (containerRef.current) {
      const container = containerRef.current;
      container.scrollLeft = container.scrollWidth;
    }
  }, [events]);

  const getEventIcon = (type: Event['type']) => {
    switch (type) {
      case 'message':
        return <MessageSquare className="w-3 h-3" />;
      case 'node_discovered':
        return <Radio className="w-3 h-3" />;
      case 'position':
        return <MapPin className="w-3 h-3" />;
      case 'telemetry':
        return <Battery className="w-3 h-3" />;
      case 'connection':
        return <Link2 className="w-3 h-3" />;
    }
  };

  const getEventColor = (type: Event['type']) => {
    switch (type) {
      case 'message':
        return 'text-cyan-400';
      case 'node_discovered':
        return 'text-green-400';
      case 'position':
        return 'text-purple-400';
      case 'telemetry':
        return 'text-yellow-400';
      case 'connection':
        return 'text-blue-400';
    }
  };

  // Keep only the most recent events
  const recentEvents = events.slice(-maxEvents);

  return (
    <div className="h-12 bg-gray-900 border-t border-gray-700 flex items-center px-4">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-400 mr-4">
        <span>Event Ticker:</span>
      </div>
      
      <div 
        ref={containerRef}
        className="flex-1 overflow-x-auto scrollbar-hide flex items-center gap-4"
        style={{ scrollBehavior: 'smooth' }}
      >
        {recentEvents.map((event) => (
          <div
            key={event.id}
            className="flex items-center gap-2 text-sm whitespace-nowrap animate-slide-up"
          >
            <span className={getEventColor(event.type)}>
              {getEventIcon(event.type)}
            </span>
            <span className="text-gray-300">{event.text}</span>
            <span className="text-gray-600 text-xs">
              {event.timestamp.toLocaleTimeString()}
            </span>
            <span className="text-gray-700">→</span>
          </div>
        ))}
        
        {recentEvents.length === 0 && (
          <span className="text-gray-600 text-sm">Waiting for events...</span>
        )}
      </div>
      
      <style>{`
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
};

export default EventTicker;
export type { Event };