'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard, Users, Building2, Clock, CalendarDays,
  Timer, DollarSign, FileText, UserPlus, BarChart3,
  GraduationCap, Package, Settings, ChevronLeft,
  ChevronRight, LogOut, Brain, Bot,
} from 'lucide-react';
import { toast } from 'sonner';

import { cn }           from '@/lib/utils';
import { getInitials }  from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';
import { logoutUser }   from '@/lib/auth';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip';
import { Separator } from '@/components/ui/separator';

// ─── Navigation definition ────────────────────────────────────────────────────

interface NavItem {
  label:      string;
  href:       string;
  icon:       React.ElementType;
  permission?: { module: string; action: string };
}

interface NavGroup {
  heading: string;
  items:   NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    heading: 'PEOPLE',
    items: [
      { label: 'Dashboard',   href: '/dashboard',   icon: LayoutDashboard },
      { label: 'Employees',   href: '/employees',   icon: Users,
        permission: { module: 'employee_management', action: 'read' } },
      { label: 'Departments', href: '/departments', icon: Building2,
        permission: { module: 'employee_management', action: 'read' } },
    ],
  },
  {
    heading: 'TIME & ATTENDANCE',
    items: [
      { label: 'Attendance',   href: '/attendance', icon: Clock,
        permission: { module: 'attendance', action: 'read' } },
      { label: 'Leave',        href: '/leave',      icon: CalendarDays,
        permission: { module: 'leave', action: 'read' } },
      { label: 'Shifts',       href: '/shifts',     icon: Timer,
        permission: { module: 'attendance', action: 'read' } },
    ],
  },
  {
    heading: 'PAYROLL',
    items: [
      { label: 'Payroll',         href: '/payroll',     icon: DollarSign,
        permission: { module: 'payroll', action: 'read' } },
      { label: 'Tax & Compliance', href: '/payroll/tax', icon: FileText,
        permission: { module: 'payroll', action: 'read' } },
    ],
  },
  {
    heading: 'TALENT',
    items: [
      { label: 'Recruitment',  href: '/recruitment',  icon: UserPlus,
        permission: { module: 'recruitment', action: 'read' } },
      { label: 'Performance',  href: '/performance',  icon: BarChart3,
        permission: { module: 'performance', action: 'read' } },
      { label: 'Training',     href: '/training',     icon: GraduationCap,
        permission: { module: 'training', action: 'read' } },
    ],
  },
  {
    heading: 'ADMIN',
    items: [
      { label: 'Assets',   href: '/assets',   icon: Package,
        permission: { module: 'assets', action: 'read' } },
      { label: 'Reports',  href: '/reports',  icon: BarChart3,
        permission: { module: 'analytics', action: 'read' } },
      { label: 'Settings', href: '/settings', icon: Settings },
    ],
  },
  {
    heading: 'AGENT FACTORY',
    items: [
      { label: 'Agent Dashboard', href: '/agent-dashboard', icon: Bot },
    ],
  },
];

// ─── Component ────────────────────────────────────────────────────────────────

interface SidebarProps {
  /** Controlled from parent (dashboard layout) for mobile overlay */
  mobileOpen?:    boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ mobileOpen = false, onMobileClose }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname  = usePathname();
  const router    = useRouter();
  const user      = useAuthStore((s) => s.user);
  const hasPermission = useAuthStore((s) => s.hasPermission);

  async function handleLogout() {
    await logoutUser();
    toast.success('Logged out successfully');
    router.push('/login');
  }

  function isActive(href: string): boolean {
    if (href === '/dashboard') return pathname === '/dashboard';
    return pathname === href || pathname.startsWith(href + '/');
  }

  // ── Shared content ──────────────────────────────────────────────────────────
  const sidebarContent = (
    <div className={cn(
      'flex flex-col h-full bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 transition-all duration-300',
      collapsed ? 'w-16' : 'w-64',
    )}>
      {/* ── Logo ─────────────────────────────────────────────────────────── */}
      <div className={cn(
        'flex items-center h-16 px-4 border-b border-slate-100 dark:border-slate-800 shrink-0',
        collapsed ? 'justify-center' : 'justify-between',
      )}>
        {!collapsed && (
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-hrms-600 rounded-lg flex items-center justify-center">
              <Brain className="w-4.5 h-4.5 text-white" />
            </div>
            <span className="font-bold text-slate-800 dark:text-slate-100 text-sm">AI-HRMS</span>
          </Link>
        )}
        {collapsed && (
          <Link href="/dashboard">
            <div className="w-8 h-8 bg-hrms-600 rounded-lg flex items-center justify-center">
              <Brain className="w-4.5 h-4.5 text-white" />
            </div>
          </Link>
        )}
        {/* Collapse toggle — desktop only */}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className={cn(
            'hidden lg:flex w-6 h-6 rounded-md items-center justify-center text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 transition-colors',
            collapsed && 'absolute right-0 translate-x-1/2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm rounded-full',
          )}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-3.5 w-3.5" />
          ) : (
            <ChevronLeft className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {/* ── Nav ──────────────────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
        <TooltipProvider delayDuration={0}>
          {NAV_GROUPS.map((group) => {
            const visibleItems = group.items.filter((item) =>
              !item.permission ||
              hasPermission(item.permission.module, item.permission.action),
            );
            if (visibleItems.length === 0) return null;

            return (
              <div key={group.heading}>
                {!collapsed && (
                  <p className="px-2 mb-1 text-[10px] font-semibold tracking-wider text-slate-400 dark:text-slate-500 uppercase">
                    {group.heading}
                  </p>
                )}
                <ul className="space-y-0.5">
                  {visibleItems.map((item) => {
                    const active  = isActive(item.href);
                    const Icon    = item.icon;
                    const linkEl  = (
                      <Link
                        href={item.href}
                        onClick={onMobileClose}
                        className={cn(
                          'flex items-center gap-3 rounded-lg px-2 py-2 text-sm font-medium transition-colors',
                          active
                            ? 'bg-hrms-50 text-hrms-700 dark:bg-hrms-950/40 dark:text-hrms-300'
                            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-800 dark:hover:text-slate-200',
                          collapsed && 'justify-center px-0',
                        )}
                      >
                        <Icon className={cn(
                          'h-4 w-4 shrink-0',
                          active ? 'text-hrms-600' : 'text-slate-400',
                        )} />
                        {!collapsed && item.label}
                      </Link>
                    );

                    return (
                      <li key={item.href}>
                        {collapsed ? (
                          <Tooltip>
                            <TooltipTrigger asChild>{linkEl}</TooltipTrigger>
                            <TooltipContent side="right">{item.label}</TooltipContent>
                          </Tooltip>
                        ) : linkEl}
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </TooltipProvider>
      </nav>

      {/* ── User footer ──────────────────────────────────────────────────── */}
      <div className="shrink-0 border-t border-slate-100 dark:border-slate-800 p-3">
        <TooltipProvider delayDuration={0}>
          <div className={cn('flex items-center gap-2', collapsed && 'flex-col')}>
            <Avatar className="w-8 h-8 shrink-0">
              <AvatarImage src={user?.avatar_url ?? undefined} alt={user?.full_name} />
              <AvatarFallback className="bg-hrms-100 text-hrms-700 text-xs font-semibold">
                {user ? getInitials(user.full_name) : '?'}
              </AvatarFallback>
            </Avatar>

            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-100 truncate">
                  {user?.full_name ?? 'Loading…'}
                </p>
                <p className="text-[10px] text-slate-400 truncate">{user?.email}</p>
              </div>
            )}

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={handleLogout}
                  className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors shrink-0"
                  aria-label="Logout"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side={collapsed ? 'right' : 'top'}>Sign out</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>
    </div>
  );

  return (
    <>
      {/* ── Desktop sidebar ─────────────────────────────────────────────── */}
      <div className="hidden lg:block relative h-full">
        {sidebarContent}
      </div>

      {/* ── Mobile drawer overlay ────────────────────────────────────────── */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
            onClick={onMobileClose}
            aria-hidden
          />
          <div className="fixed inset-y-0 left-0 z-50 lg:hidden">
            {sidebarContent}
          </div>
        </>
      )}
    </>
  );
}
