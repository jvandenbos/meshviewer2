import React from 'react';
import { Router, Circle, Diamond, Square } from 'lucide-react';

const Legend: React.FC = () => {
  return (
    <div className="absolute bottom-4 left-4 bg-gray-800 bg-opacity-90 rounded-lg p-4 shadow-lg">
      <h3 className="text-sm font-semibold text-white mb-3">Legend</h3>
      
      {/* Node Types */}
      <div className="space-y-2 text-xs">
        <div className="flex items-center gap-2">
          <Circle className="w-4 h-4 text-green-500 fill-green-500" />
          <span className="text-gray-300">My Node (Local)</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Diamond className="w-4 h-4 text-purple-500 fill-purple-500" />
          <span className="text-gray-300">Router</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Circle className="w-4 h-4 text-cyan-500 fill-cyan-500" />
          <span className="text-gray-300">Client</span>
        </div>
        
        <div className="border-t border-gray-700 pt-2 mt-2">
          <div className="text-gray-400 mb-1">Signal Quality</div>
          <div className="flex items-center gap-2">
            <Circle className="w-3 h-3 text-green-500 fill-green-500" />
            <span className="text-gray-300">Excellent</span>
          </div>
          <div className="flex items-center gap-2">
            <Circle className="w-3 h-3 text-yellow-500 fill-yellow-500" />
            <span className="text-gray-300">Good</span>
          </div>
          <div className="flex items-center gap-2">
            <Circle className="w-3 h-3 text-orange-500 fill-orange-500" />
            <span className="text-gray-300">Weak</span>
          </div>
          <div className="flex items-center gap-2">
            <Circle className="w-3 h-3 text-red-500 fill-red-500" />
            <span className="text-gray-300">Poor</span>
          </div>
        </div>
        
        <div className="border-t border-gray-700 pt-2 mt-2">
          <div className="text-gray-400 mb-1">Node Size = Distance</div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <div className="w-5 h-5 bg-cyan-500 rounded-full"></div>
              <span className="text-gray-300">0 hops</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 bg-cyan-500 rounded-full"></div>
              <span className="text-gray-300">1 hop</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-cyan-500 rounded-full"></div>
              <span className="text-gray-300">2+ hops</span>
            </div>
          </div>
        </div>
        
        <div className="border-t border-gray-700 pt-2 mt-2">
          <div className="text-gray-400 mb-1">Link Types</div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-cyan-500"></div>
            <span className="text-gray-300">Direct</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-gray-500 border-b-2 border-dashed border-gray-500"></div>
            <span className="text-gray-300">Multi-hop</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Legend;