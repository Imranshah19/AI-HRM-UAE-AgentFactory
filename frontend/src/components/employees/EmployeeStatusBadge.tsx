import { cn } from '@/lib/utils';
import type { EmployeeStatus } from '@/types/employee';

interface StatusConfig {
  label: string;
  classes: string;
}

const STATUS_CONFIG: Record<EmployeeStatus, StatusConfig> = {
  active:     { label: 'Active',     classes: 'bg-green-100 text-green-700 border-green-200' },
  inactive:   { label: 'Inactive',   classes: 'bg-slate-100 text-slate-600 border-slate-200' },
  on_leave:   { label: 'On Leave',   classes: 'bg-purple-100 text-purple-700 border-purple-200' },
  suspended:  { label: 'Suspended',  classes: 'bg-orange-100 text-orange-700 border-orange-200' },
  terminated: { label: 'Terminated', classes: 'bg-red-100 text-red-700 border-red-200' },
  resigned:   { label: 'Resigned',   classes: 'bg-amber-100 text-amber-700 border-amber-200' },
};

interface EmployeeStatusBadgeProps {
  status:    EmployeeStatus;
  className?: string;
  size?:     'sm' | 'md';
}

export function EmployeeStatusBadge({
  status,
  className,
  size = 'md',
}: EmployeeStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? {
    label:   status,
    classes: 'bg-slate-100 text-slate-600 border-slate-200',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-0.5 text-xs',
        config.classes,
        className,
      )}
    >
      <span
        className={cn(
          'mr-1.5 rounded-full',
          size === 'sm' ? 'w-1.5 h-1.5' : 'w-1.5 h-1.5',
          status === 'active'    ? 'bg-green-500' :
          status === 'on_leave'  ? 'bg-purple-500' :
          status === 'suspended' ? 'bg-orange-500' :
          status === 'terminated'? 'bg-red-500' :
          status === 'resigned'  ? 'bg-amber-500' :
          'bg-slate-400',
        )}
      />
      {config.label}
    </span>
  );
}
