import React, { useEffect, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import { NodeInfo, NetworkLink } from '../types';

// Register the force-directed layout
cytoscape.use(coseBilkent);

interface NetworkGraphProps {
  nodes: NodeInfo[];
  links: NetworkLink[];
  onNodeClick?: (node: NodeInfo) => void;
  onNodeHover?: (node: NodeInfo | null) => void;
}

const NetworkGraph: React.FC<NetworkGraphProps> = ({ 
  nodes, 
  links, 
  onNodeClick, 
  onNodeHover 
}) => {
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Convert nodes to Cytoscape elements
  const elements = React.useMemo(() => {
    const nodeElements = nodes.map(node => ({
      data: {
        id: node.id,
        label: node.short_name,
        ...node
      },
      classes: [
        node.signal_quality || 'unknown',
        node.is_online ? 'online' : 'offline'
      ].join(' ')
    }));

    // Create a set of valid node IDs for quick lookup
    const nodeIds = new Set(nodes.map(n => n.id));

    // Only create edges between existing nodes
    const edgeElements = links
      .filter(link => nodeIds.has(link.from_id) && nodeIds.has(link.to_id))
      .map(link => ({
        data: {
          id: `${link.from_id}-${link.to_id}`,
          source: link.from_id,
          target: link.to_id,
          weight: link.success_rate,
          rssi: link.rssi,
          is_direct: link.is_direct
        },
        classes: link.is_direct ? 'direct' : 'multihop'
      }));

    return [...nodeElements, ...edgeElements];
  }, [nodes, links]);

  // Cytoscape stylesheet
  const stylesheet: cytoscape.Stylesheet[] = [
    {
      selector: 'node',
      style: {
        'background-color': '#06b6d4',
        'label': 'data(label)',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'font-size': '12px',
        'color': '#ffffff',
        'width': 40,
        'height': 40,
        'border-width': 2,
        'border-color': '#0891b2',
        'text-margin-y': 5
      }
    },
    {
      selector: 'node.excellent',
      style: {
        'background-color': '#22c55e',
        'border-color': '#16a34a'
      }
    },
    {
      selector: 'node.good',
      style: {
        'background-color': '#eab308',
        'border-color': '#ca8a04'
      }
    },
    {
      selector: 'node.weak',
      style: {
        'background-color': '#f97316',
        'border-color': '#ea580c'
      }
    },
    {
      selector: 'node.poor',
      style: {
        'background-color': '#ef4444',
        'border-color': '#dc2626'
      }
    },
    {
      selector: 'node.offline',
      style: {
        'opacity': 0.5,
        'background-color': '#6b7280'
      }
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 4,
        'border-color': '#3b82f6',
        'background-color': '#2563eb'
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#4b5563',
        'target-arrow-color': '#4b5563',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.7
      }
    },
    {
      selector: 'edge.direct',
      style: {
        'line-color': '#06b6d4',
        'target-arrow-color': '#06b6d4',
        'width': 3
      }
    },
    {
      selector: 'edge.multihop',
      style: {
        'line-style': 'dashed',
        'line-dash-pattern': [6, 3]
      }
    }
  ];

  // Handle node events
  useEffect(() => {
    if (!cyRef.current) return;

    const cy = cyRef.current;

    // Node click handler
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const nodeData = node.data() as NodeInfo;
      setSelectedNodeId(nodeData.id);
      if (onNodeClick) {
        onNodeClick(nodeData);
      }
    });

    // Node hover handlers
    cy.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      const nodeData = node.data() as NodeInfo;
      node.addClass('hover');
      if (onNodeHover) {
        onNodeHover(nodeData);
      }
    });

    cy.on('mouseout', 'node', (evt) => {
      const node = evt.target;
      node.removeClass('hover');
      if (onNodeHover) {
        onNodeHover(null);
      }
    });

    // Background click to deselect
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNodeId(null);
      }
    });

    return () => {
      cy.removeAllListeners();
    };
  }, [onNodeClick, onNodeHover]);

  // Animate new nodes
  useEffect(() => {
    if (!cyRef.current) return;

    const cy = cyRef.current;
    
    // Find newly added nodes
    cy.nodes().forEach((node) => {
      if (!node.data('animated')) {
        node.data('animated', true);
        node.animate({
          style: {
            'width': 60,
            'height': 60
          },
          duration: 300
        }).animate({
          style: {
            'width': 40,
            'height': 40
          },
          duration: 300
        });
      }
    });
  }, [nodes]);

  return (
    <div className="w-full h-full bg-gray-900 rounded-lg">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={stylesheet}
        cy={(cy) => { cyRef.current = cy; }}
        layout={{
          name: 'cose-bilkent',
          animate: true,
          animationDuration: 500,
          fit: true,
          padding: 30,
          nodeRepulsion: 8000,
          idealEdgeLength: 100,
          edgeElasticity: 0.45,
          nestingFactor: 0.1,
          gravity: 0.25,
          numIter: 2500,
          tile: true,
          tilingPaddingVertical: 10,
          tilingPaddingHorizontal: 10,
          gravityRangeCompound: 1.5,
          gravityCompound: 1.0,
          gravityRange: 3.8
        }}
        pan={{ x: 0, y: 0 }}
        zoom={1}
        minZoom={0.1}
        maxZoom={3}
        wheelSensitivity={0.2}
      />
    </div>
  );
};

export default NetworkGraph;