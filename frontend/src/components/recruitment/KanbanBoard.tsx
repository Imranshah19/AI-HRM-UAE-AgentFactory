'use client';

import { useState, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS }        from '@dnd-kit/utilities';
import { Mail, GripVertical } from 'lucide-react';

import { Badge }   from '@/components/ui/badge';
import { AIScoreCard } from './AIScoreCard';
import { usePipelineStats, useUpdateStage } from '@/hooks/useRecruitment';
import type { ApplicationStatus, JobApplicationListItem, PipelineStats } from '@/types/recruitment';

// ─── Column config ────────────────────────────────────────────────────────────

interface ColumnDef {
  status: ApplicationStatus;
  label:  string;
  color:  string;
  dot:    string;
}

const COLUMNS: ColumnDef[] = [
  { status: 'applied',     label: 'Applied',     color: 'border-slate-300',   dot: 'bg-slate-400' },
  { status: 'screening',   label: 'Screening',   color: 'border-blue-300',    dot: 'bg-blue-500' },
  { status: 'shortlisted', label: 'Shortlisted', color: 'border-indigo-300',  dot: 'bg-indigo-500' },
  { status: 'interview',   label: 'Interview',   color: 'border-violet-300',  dot: 'bg-violet-500' },
  { status: 'offered',     label: 'Offered',     color: 'border-amber-300',   dot: 'bg-amber-500' },
  { status: 'hired',       label: 'Hired',       color: 'border-green-400',   dot: 'bg-green-500' },
];

// ─── Application card ─────────────────────────────────────────────────────────

function AppCard({
  app,
  isDragging = false,
  onClick,
}: {
  app:         JobApplicationListItem;
  isDragging?: boolean;
  onClick?:    () => void;
}) {
  return (
    <div
      className={`bg-white rounded-lg border p-3 space-y-2 cursor-pointer select-none
        ${isDragging ? 'shadow-lg rotate-1 opacity-90' : 'shadow-sm hover:shadow-md'}
        transition-shadow`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-slate-800 leading-tight truncate">
          {app.candidate_name}
        </p>
        <GripVertical className="h-4 w-4 text-slate-300 shrink-0 mt-0.5" />
      </div>
      <div className="flex items-center gap-1.5 text-xs text-slate-500 truncate">
        <Mail className="h-3 w-3 shrink-0" />
        {app.candidate_email}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400 capitalize">
          {app.source.replace('_', ' ')}
        </span>
        {app.ai_score !== null && (
          <AIScoreCard score={app.ai_score} compact />
        )}
      </div>
    </div>
  );
}

// ─── Sortable card wrapper ────────────────────────────────────────────────────

function SortableCard({
  app,
  onClick,
}: {
  app:     JobApplicationListItem;
  onClick: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: app.id, data: { status: app.status } });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...attributes}
      {...listeners}
      className={isDragging ? 'opacity-40' : ''}
    >
      <AppCard app={app} onClick={isDragging ? undefined : onClick} />
    </div>
  );
}

// ─── Droppable column ─────────────────────────────────────────────────────────

function KanbanColumn({
  col,
  apps,
  onCardClick,
  isOver = false,
}: {
  col:         ColumnDef;
  apps:        JobApplicationListItem[];
  onCardClick: (id: string) => void;
  isOver?:     boolean;
}) {
  return (
    <div className={`flex flex-col w-64 shrink-0 rounded-xl border-2 ${col.color}
      ${isOver ? 'bg-slate-50' : 'bg-slate-50/50'} transition-colors`}
    >
      {/* Column header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-slate-200">
        <span className={`h-2 w-2 rounded-full ${col.dot}`} />
        <span className="text-sm font-semibold text-slate-700">{col.label}</span>
        <Badge variant="secondary" className="ml-auto text-xs py-0 px-1.5">
          {apps.length}
        </Badge>
      </div>

      {/* Cards */}
      <SortableContext
        items={apps.map((a) => a.id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-20 max-h-[calc(100vh-260px)]">
          {apps.map((app) => (
            <SortableCard
              key={app.id}
              app={app}
              onClick={() => onCardClick(app.id)}
            />
          ))}
          {apps.length === 0 && (
            <div className="flex items-center justify-center h-16 rounded-lg border-2 border-dashed border-slate-200">
              <span className="text-xs text-slate-400">Drop here</span>
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

// ─── Main board ───────────────────────────────────────────────────────────────

interface Props {
  jobId:       string;
  onCardClick: (applicationId: string) => void;
}

export function KanbanBoard({ jobId, onCardClick }: Props) {
  const { data: pipeline, isLoading } = usePipelineStats(jobId);
  const updateStage                   = useUpdateStage();

  // Optimistic local state: map appId → status override
  const [overrides, setOverrides] = useState<Record<string, ApplicationStatus>>({});
  const [activeApp, setActiveApp] = useState<JobApplicationListItem | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  // Merge server data with optimistic overrides
  const allApps = useCallback((): JobApplicationListItem[] => {
    if (!pipeline) return [];
    return pipeline.columns.flatMap((col) => col.applications).map((app) => ({
      ...app,
      status: (overrides[app.id] as ApplicationStatus) ?? app.status,
    }));
  }, [pipeline, overrides]);

  function getColumnApps(status: ApplicationStatus): JobApplicationListItem[] {
    return allApps().filter((a) => a.status === status);
  }

  function findApp(id: string): JobApplicationListItem | undefined {
    return allApps().find((a) => a.id === id);
  }

  function onDragStart(event: DragStartEvent) {
    const app = findApp(event.active.id as string);
    if (app) setActiveApp(app);
  }

  function onDragEnd(event: DragEndEvent) {
    setActiveApp(null);

    const { active, over } = event;
    if (!over) return;

    const appId     = active.id as string;
    const overId    = over.id   as string;
    const app       = findApp(appId);
    if (!app) return;

    // Determine target status — either the column id or the app's status in the column
    let targetStatus: ApplicationStatus | undefined;

    // Check if dropped on a column id (same as status string)
    if (COLUMNS.find((c) => c.status === overId)) {
      targetStatus = overId as ApplicationStatus;
    } else {
      // Dropped on another card — use that card's status
      const targetApp = findApp(overId);
      targetStatus = targetApp?.status;
    }

    if (!targetStatus || targetStatus === app.status) return;

    // Optimistic update
    setOverrides((prev) => ({ ...prev, [appId]: targetStatus! }));

    // Server update
    updateStage.mutate(
      { id: appId, data: { new_status: targetStatus } },
      {
        onError: () => {
          // Rollback on failure
          setOverrides((prev) => {
            const next = { ...prev };
            delete next[appId];
            return next;
          });
        },
        onSuccess: () => {
          // Remove override — server data now up to date
          setOverrides((prev) => {
            const next = { ...prev };
            delete next[appId];
            return next;
          });
        },
      },
    );
  }

  if (isLoading) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((col) => (
          <div key={col.status} className="w-64 shrink-0 h-48 rounded-xl bg-slate-100 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div className="text-sm text-slate-500 italic py-8 text-center">
        No pipeline data available.
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4 pt-1">
        {COLUMNS.map((col) => (
          <KanbanColumn
            key={col.status}
            col={col}
            apps={getColumnApps(col.status)}
            onCardClick={onCardClick}
          />
        ))}
      </div>

      {/* Drag overlay (floating card) */}
      <DragOverlay>
        {activeApp && <AppCard app={activeApp} isDragging />}
      </DragOverlay>
    </DndContext>
  );
}
