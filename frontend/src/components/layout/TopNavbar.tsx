'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Menu, Search, ChevronDown, User, KeyRound, LogOut } from 'lucide-react';
import { toast } from 'sonner';

import { cn }          from '@/lib/utils';
import { getInitials } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';
import { logoutUser }   from '@/lib/auth';
import { Breadcrumb }   from './Breadcrumb';
import { NotificationPanel } from '@/components/notifications/NotificationPanel';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

// ─── Component ────────────────────────────────────────────────────────────────

interface TopNavbarProps {
  onMenuClick: () => void;
}

export function TopNavbar({ onMenuClick }: TopNavbarProps) {
  const router = useRouter();
  const user   = useAuthStore((s) => s.user);

  async function handleLogout() {
    await logoutUser();
    toast.success('Logged out');
    router.push('/login');
  }

  return (
    <header className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 sm:px-6 shrink-0">
      {/* ── Left ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-1.5 rounded-md text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          aria-label="Open navigation"
        >
          <Menu className="h-5 w-5" />
        </button>
        <Breadcrumb className="hidden sm:flex" />
      </div>

      {/* ── Right ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1 sm:gap-2">
        {/* Search */}
        <Button
          variant="ghost"
          size="icon"
          className="text-slate-500 hover:text-slate-700"
          aria-label="Search"
        >
          <Search className="h-4 w-4" />
        </Button>

        {/* Notifications — live badge via NotificationPanel */}
        <NotificationPanel />

        {/* User dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ml-1">
              <Avatar className="w-7 h-7">
                <AvatarImage src={user?.avatar_url ?? undefined} alt={user?.full_name} />
                <AvatarFallback className="bg-hrms-100 text-hrms-700 text-xs font-semibold">
                  {user ? getInitials(user.full_name) : '?'}
                </AvatarFallback>
              </Avatar>
              <span className="hidden sm:block text-sm font-medium text-slate-700 dark:text-slate-300 max-w-[120px] truncate">
                {user?.first_name}
              </span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            </button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-0.5">
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {user?.full_name}
                </p>
                <p className="text-xs text-slate-500 truncate">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />

            <DropdownMenuItem asChild>
              <Link href="/profile" className="flex items-center gap-2 cursor-pointer">
                <User className="h-4 w-4" />
                My Profile
              </Link>
            </DropdownMenuItem>

            <DropdownMenuItem asChild>
              <Link href="/settings" className="flex items-center gap-2 cursor-pointer">
                <KeyRound className="h-4 w-4" />
                Settings
              </Link>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              onClick={handleLogout}
              className="text-red-600 dark:text-red-400 focus:text-red-700 focus:bg-red-50 dark:focus:bg-red-900/20 cursor-pointer"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
