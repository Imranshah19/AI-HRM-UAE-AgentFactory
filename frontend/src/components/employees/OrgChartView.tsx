'use client';

import { useState, useCallback } from 'react';
import { ChevronDown, ChevronRight, Users } from 'lucide-react';
import { cn }           from '@/lib/utils';
import { EmployeeAvatar } from './EmployeeAvatar';
import type { OrgChartNode } from '@/types/employee';

// ─── Single node card ─────────────────────────────────────────────────────────

interface NodeCardProps {
  node:       OrgChartNode;
  isRoot?:    boolean;
  onSelect?:  (id: string) => void;
}

function NodeCard({ node, isRoot, onSelect }: NodeCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(node.id)}
      className={cn(
        'group flex flex-col items-center gap-1.5 p-3 rounded-xl border bg-white dark:bg-slate-900',
        'shadow-sm hover:shadow-md transition-shadow text-left w-36',
        isRoot && 'border-hrms-400 ring-2 ring-hrms-200 dark:ring-hrms-900',
      )}
    >
      <EmployeeAvatar
        name={node.full_name}
        photoUrl={node.photo_url}
        size="md"
      />
      <div className="w-full text-center">
        <p className="text-xs font-semibold text-slate-800 dark:text-slate-100 truncate leading-tight">
          {node.full_name}
        </p>
        {node.designation && (
          <p className="text-[10px] text-slate-500 truncate">{node.designation}</p>
        )}
        {node.department && (
          <p className="text-[10px] text-hrms-600 dark:text-hrms-400 truncate">{node.department}</p>
        )}
      </div>
    </button>
  );
}

// ─── Recursive tree node ──────────────────────────────────────────────────────

interface TreeNodeProps {
  node:      OrgChartNode;
  depth:     number;
  onSelect?: (id: string) => void;
}

function TreeNode({ node, depth, onSelect }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className="flex flex-col items-center">
      {/* Card + expand toggle */}
      <div className="relative">
        <NodeCard node={node} isRoot={depth === 0} onSelect={onSelect} />
        {hasChildren && (
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className={cn(
              'absolute -bottom-3 left-1/2 -translate-x-1/2',
              'flex items-center justify-center w-6 h-6 rounded-full',
              'bg-white dark:bg-slate-800 border shadow-sm text-slate-500',
              'hover:text-hrms-600 hover:border-hrms-400 transition-colors z-10',
            )}
            title={expanded ? 'Collapse' : `Expand (${node.children!.length})`}
          >
            {expanded
              ? <ChevronDown  className="h-3.5 w-3.5" />
              : <ChevronRight className="h-3.5 w-3.5" />
            }
          </button>
        )}
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div className="mt-6 relative">
          {/* Vertical connector from parent */}
          <div className="absolute top-0 left-1/2 -translate-x-px w-px h-4 bg-slate-300 dark:bg-slate-600" />

          {/* Horizontal bar */}
          {node.children!.length > 1 && (
            <div
              className="absolute top-4 bg-slate-300 dark:bg-slate-600 h-px"
              style={{
                // spans from first child centre to last child centre
                left:  `calc(${100 / (2 * node.children!.length)}%)`,
                right: `calc(${100 / (2 * node.children!.length)}%)`,
              }}
            />
          )}

          <div className="flex gap-6 mt-4">
            {node.children!.map((child) => (
              <div key={child.id} className="relative flex flex-col items-center">
                {/* Vertical connector to child */}
                <div className="absolute -top-4 left-1/2 -translate-x-px w-px h-4 bg-slate-300 dark:bg-slate-600" />
                <TreeNode node={child} depth={depth + 1} onSelect={onSelect} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Collapsed indicator */}
      {hasChildren && !expanded && (
        <div className="mt-6 flex items-center gap-1 text-[10px] text-slate-400">
          <Users className="h-3 w-3" />
          {node.children!.length} report{node.children!.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface OrgChartViewProps {
  nodes:     OrgChartNode[];
  onSelect?: (id: string) => void;
  className?: string;
}

export function OrgChartView({ nodes, onSelect, className }: OrgChartViewProps) {
  const handleSelect = useCallback((id: string) => onSelect?.(id), [onSelect]);

  if (!nodes.length) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-400">
        <Users className="h-12 w-12 mb-3 opacity-30" />
        <p className="text-sm">No org chart data available.</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'overflow-auto p-8 min-h-64',
        className,
      )}
    >
      <div className="flex gap-12 justify-center">
        {nodes.map((root) => (
          <TreeNode key={root.id} node={root} depth={0} onSelect={handleSelect} />
        ))}
      </div>
    </div>
  );
}
