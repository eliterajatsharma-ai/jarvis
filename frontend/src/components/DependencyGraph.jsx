import React from 'react';
import { Database, Server, Globe, Cpu } from 'lucide-react';

const NODE_CONFIG = {
  'web-gateway': { cx: 400, cy: 36, icon: Globe, label: 'web-gateway', tier: 'gateway' },
  'auth-service': { cx: 230, cy: 122, icon: Server, label: 'auth-service', tier: 'service' },
  'payment-api': { cx: 570, cy: 122, icon: Server, label: 'payment-api', tier: 'service' },
  'redis-cache': { cx: 110, cy: 208, icon: Cpu, label: 'redis-cache', tier: 'cache' },
  'user-db': { cx: 290, cy: 208, icon: Database, label: 'user-db', tier: 'database' },
  'orders-db': { cx: 510, cy: 208, icon: Database, label: 'orders-db', tier: 'database' },
  'payment-gateway': { cx: 690, cy: 208, icon: Globe, label: 'payment-gateway', tier: 'external' }
};

const CARD_W = 126;
const CARD_H = 44;

const EDGES = [
  { from: 'web-gateway', to: 'auth-service', id: 'e1', x1: 400, y1: 58, x2: 230, y2: 100 },
  { from: 'web-gateway', to: 'payment-api', id: 'e2', x1: 400, y1: 58, x2: 570, y2: 100 },
  { from: 'auth-service', to: 'redis-cache', id: 'e3', x1: 230, y1: 144, x2: 110, y2: 186 },
  { from: 'auth-service', to: 'user-db', id: 'e4', x1: 230, y1: 144, x2: 290, y2: 186 },
  { from: 'payment-api', to: 'orders-db', id: 'e5', x1: 570, y1: 144, x2: 510, y2: 186 },
  { from: 'payment-api', to: 'payment-gateway', id: 'e6', x1: 570, y1: 144, x2: 690, y2: 186 }
];

export default function DependencyGraph({
  topology,
  activeIncident,
  selectedService,
  onSelectService,
  scrubberValue = 100
}) {
  const rootCauseSvc = activeIncident?.root_cause_candidates?.[0]?.service;
  const blastRadius = activeIncident?.impact?.blast_radius_nodes || [];
  const isEarlyScrub = scrubberValue < 40;

  return (
    <div className="relative w-full h-[260px] bg-[#090e1a] rounded-xl border border-slate-800/80 p-2 overflow-hidden shadow-2xl flex items-center justify-center">
      {/* Background HUD Grid */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20">
        <defs>
          <pattern id="hud-grid-clean" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#00f0ff" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#hud-grid-clean)" />
      </svg>

      {/* Fully Responsive Vector Canvas (Scales in Lockstep on ALL screen resolutions) */}
      <svg
        className="w-full h-full"
        viewBox="0 0 800 250"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <marker id="arrow-clean" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#38bdf8" />
          </marker>
          <marker id="arrow-clean-error" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#ff3366" />
          </marker>
        </defs>

        {/* Directed Causal Edges */}
        {EDGES.map(edge => {
          const isFailingEdge = (edge.to === rootCauseSvc || edge.from === rootCauseSvc) && !isEarlyScrub;
          const strokeColor = isFailingEdge ? '#ff3366' : (blastRadius.includes(edge.to) ? '#f59e0b' : '#1e293b');
          const markerId = isFailingEdge ? 'url(#arrow-clean-error)' : 'url(#arrow-clean)';

          return (
            <g key={edge.id}>
              <line
                x1={edge.x1}
                y1={edge.y1}
                x2={edge.x2}
                y2={edge.y2}
                stroke={strokeColor}
                strokeWidth={isFailingEdge ? 2.2 : 1.4}
                strokeDasharray={isFailingEdge ? '4 3' : 'none'}
                markerEnd={markerId}
                className={isFailingEdge ? 'animate-pulse' : ''}
              />
              {/* Animated particle pulse for active cascades */}
              {isFailingEdge && (
                <circle r="3.5" fill="#ff3366">
                  <animateMotion
                    path={`M ${edge.x1} ${edge.y1} L ${edge.x2} ${edge.y2}`}
                    dur="1.4s"
                    repeatCount="indefinite"
                  />
                </circle>
              )}
            </g>
          );
        })}

        {/* Node Cards Rendered via foreignObject inside SVG */}
        {Object.entries(NODE_CONFIG).map(([nodeId, cfg]) => {
          const IconComponent = cfg.icon;
          const isRootCause = nodeId === rootCauseSvc;
          const isImpacted = blastRadius.includes(nodeId);
          const isSelected = selectedService === nodeId;

          // Status state
          let statusBorder = 'border-slate-800 bg-[#0c1322]/95 text-slate-300';
          let badgeText = 'HEALTHY';
          let badgeClass = 'text-emerald-400 bg-emerald-950/70 border-emerald-800/50';

          if (isRootCause) {
            statusBorder = 'border-[#ff3366] bg-[#2a0e19] text-[#ff3366] crimson-glow';
            badgeText = 'ROOT CAUSE';
            badgeClass = 'text-[#ff3366] bg-[#3b0d1e] border-[#ff3366]/60 animate-pulse font-bold';
          } else if (isImpacted && (!isEarlyScrub || nodeId === 'auth-service')) {
            statusBorder = 'border-amber-500 bg-[#281a0b] text-amber-300';
            badgeText = 'BLAST RADIUS';
            badgeClass = 'text-amber-400 bg-amber-950/70 border-amber-800/50';
          }

          if (isSelected) {
            statusBorder += ' ring-2 ring-[#00f0ff] ring-offset-2 ring-offset-[#070a12]';
          }

          return (
            <foreignObject
              key={nodeId}
              x={cfg.cx - CARD_W / 2}
              y={cfg.cy - CARD_H / 2}
              width={CARD_W}
              height={CARD_H}
              className="overflow-visible"
            >
              <div
                onClick={() => onSelectService(nodeId)}
                className={`w-full h-full cursor-pointer rounded-lg border px-2 py-1 transition-all duration-300 transform hover:scale-105 select-none shadow-xl flex flex-col justify-between ${statusBorder}`}
              >
                <div className="flex items-center space-x-1.5 truncate">
                  <IconComponent className={`w-3.5 h-3.5 shrink-0 ${isRootCause ? 'text-[#ff3366] animate-bounce' : 'text-slate-400'}`} />
                  <span className="text-[10px] font-bold font-mono tracking-tight text-slate-100 truncate">
                    {cfg.label}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[8px] font-mono">
                  <span className={`px-1 py-0.2 rounded border ${badgeClass}`}>
                    {badgeText}
                  </span>
                  {cfg.tier === 'external' && (
                    <span className="text-purple-300 bg-purple-950/80 px-1 py-0.2 rounded border border-purple-800/50">
                      EXT
                    </span>
                  )}
                </div>
              </div>
            </foreignObject>
          );
        })}
      </svg>

      {/* Legend & Watermark */}
      <div className="absolute bottom-1.5 left-2.5 flex items-center space-x-2.5 text-[9px] font-mono text-slate-400 bg-[#070a12]/90 px-2 py-0.5 rounded border border-slate-800/80 shadow">
        <span className="flex items-center space-x-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[#ff3366] animate-pulse"></span>
          <span>Root Cause</span>
        </span>
        <span className="flex items-center space-x-1">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          <span>Blast Radius</span>
        </span>
        <span className="flex items-center space-x-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>Normal SLO</span>
        </span>
      </div>
    </div>
  );
}
