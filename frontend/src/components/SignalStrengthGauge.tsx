import React from 'react';

interface SignalStrengthGaugeProps {
  rssi?: number | null;
  quality?: string | null;
  compact?: boolean;
}

const SignalStrengthGauge: React.FC<SignalStrengthGaugeProps> = ({ rssi, quality, compact = false }) => {
  // Calculate bars based on RSSI or quality
  const getBars = () => {
    if (quality) {
      switch (quality) {
        case 'excellent': return 4;
        case 'good': return 3;
        case 'weak': return 2;
        case 'poor': return 1;
        default: return 0;
      }
    }
    if (rssi) {
      if (rssi > -75) return 4;
      if (rssi > -85) return 3;
      if (rssi > -95) return 2;
      if (rssi > -120) return 1;
    }
    return 0;
  };

  const getBarColor = (barIndex: number, activeBars: number) => {
    if (barIndex >= activeBars) return 'bg-gray-700';
    if (activeBars === 4) return 'bg-green-500';
    if (activeBars === 3) return 'bg-yellow-500';
    if (activeBars === 2) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const bars = getBars();

  if (compact) {
    // Compact horizontal bars
    return (
      <div className="flex items-center gap-0.5">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`w-1 transition-all ${getBarColor(i, bars)}`}
            style={{ height: `${(i + 1) * 3}px` }}
          />
        ))}
        {rssi && (
          <span className="text-xs text-gray-500 ml-1">{rssi}dBm</span>
        )}
      </div>
    );
  }

  // Full gauge with label
  return (
    <div className="flex flex-col items-center">
      <div className="flex items-end gap-0.5 h-6">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`w-2 transition-all ${getBarColor(i, bars)}`}
            style={{ height: `${(i + 1) * 6}px` }}
          />
        ))}
      </div>
      {rssi && (
        <span className="text-xs text-gray-400 mt-1">{rssi}dBm</span>
      )}
    </div>
  );
};

export default SignalStrengthGauge;