'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { ChevronRight, Home } from 'lucide-react';
import { Fragment } from 'react';
import { cn } from '@/lib/utils';

// ─── Path → label map ────────────────────────────────────────────────────────

const PATH_LABELS: Record<string, string> = {
  dashboard:    'Dashboard',
  employees:    'Employees',
  departments:  'Departments',
  designations: 'Designations',
  attendance:   'Attendance',
  leave:        'Leave Management',
  shifts:       'Shifts',
  payroll:      'Payroll',
  tax:          'Tax & Compliance',
  recruitment:  'Recruitment',
  performance:  'Performance',
  training:     'Training',
  assets:       'Assets',
  reports:      'Reports',
  settings:     'Settings',
  new:          'New',
  edit:         'Edit',
  profile:      'My Profile',
};

function labelForSegment(segment: string): string {
  // Known labels
  if (PATH_LABELS[segment]) return PATH_LABELS[segment];

  // UUID-ish segments — likely a detail page
  if (/^[0-9a-f-]{32,36}$/i.test(segment)) return 'Detail';

  // Title-case the segment
  return segment
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Breadcrumb({ className }: { className?: string }) {
  const pathname = usePathname();

  // Remove leading slash, split, drop empty segments
  const segments = pathname.replace(/^\//, '').split('/').filter(Boolean);

  // Build cumulative href for each segment
  const crumbs = segments.map((segment, idx) => ({
    label: labelForSegment(segment),
    href:  '/' + segments.slice(0, idx + 1).join('/'),
    isLast: idx === segments.length - 1,
  }));

  if (crumbs.length === 0) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn('flex items-center gap-1 text-sm', className)}
    >
      {/* Home */}
      <Link
        href="/dashboard"
        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
        aria-label="Dashboard"
      >
        <Home className="h-3.5 w-3.5" />
      </Link>

      {crumbs.map(({ label, href, isLast }) => (
        <Fragment key={href}>
          <ChevronRight className="h-3 w-3 text-slate-300 shrink-0" />
          {isLast ? (
            <span className="font-medium text-slate-700 dark:text-slate-200 truncate max-w-[180px]">
              {label}
            </span>
          ) : (
            <Link
              href={href}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors truncate max-w-[120px]"
            >
              {label}
            </Link>
          )}
        </Fragment>
      ))}
    </nav>
  );
}
