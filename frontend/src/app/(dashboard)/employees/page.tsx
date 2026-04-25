'use client';

import { useState, useCallback } from 'react';
import { useRouter }             from 'next/navigation';
import {
  Plus, Search, Filter, Download, Users,
  ChevronLeft, ChevronRight, MoreHorizontal,
} from 'lucide-react';

import { Button }     from '@/components/ui/button';
import { Input }      from '@/components/ui/input';
import { Badge }      from '@/components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Skeleton }              from '@/components/ui/skeleton';
import { EmployeeAvatar }        from '@/components/employees/EmployeeAvatar';
import { EmployeeStatusBadge }   from '@/components/employees/EmployeeStatusBadge';
import {
  useEmployeeList, useDepartments, useExportEmployees,
} from '@/hooks/useEmployees';
import { useAuthStore }          from '@/stores/authStore';
import type { EmployeeFilters, EmployeeStatus } from '@/types/employee';

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZES = [10, 25, 50];

const STATUS_OPTIONS: { value: EmployeeStatus | 'all'; label: string }[] = [
  { value: 'all',        label: 'All statuses' },
  { value: 'active',     label: 'Active' },
  { value: 'inactive',   label: 'Inactive' },
  { value: 'on_leave',   label: 'On Leave' },
  { value: 'suspended',  label: 'Suspended' },
  { value: 'resigned',   label: 'Resigned' },
  { value: 'terminated', label: 'Terminated' },
];

// ─── Skeleton rows ────────────────────────────────────────────────────────────

function SkeletonRows({ count }: { count: number }) {
  return Array.from({ length: count }).map((_, i) => (
    <TableRow key={i}>
      <TableCell><div className="flex items-center gap-3"><Skeleton className="w-9 h-9 rounded-full" /><div className="space-y-1"><Skeleton className="h-3.5 w-32" /><Skeleton className="h-3 w-24" /></div></div></TableCell>
      <TableCell><Skeleton className="h-3.5 w-24" /></TableCell>
      <TableCell><Skeleton className="h-3.5 w-28" /></TableCell>
      <TableCell><Skeleton className="h-5 w-16 rounded-full" /></TableCell>
      <TableCell><Skeleton className="h-3.5 w-20" /></TableCell>
      <TableCell><Skeleton className="h-7 w-7 rounded" /></TableCell>
    </TableRow>
  ));
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function EmployeesPage() {
  const router     = useRouter();
  const canCreate  = useAuthStore((s) => s.hasPermission('employees', 'create'));
  const exportFn   = useExportEmployees();

  const [filters, setFilters] = useState<Partial<EmployeeFilters>>({
    page: 1, page_size: 25,
  });
  const [searchInput, setSearchInput] = useState('');

  const { data, isLoading, isFetching } = useEmployeeList(filters);
  const { data: departments = [] }      = useDepartments();

  const employees   = data?.results ?? [];
  const total       = data?.count   ?? 0;
  const currentPage = filters.page  ?? 1;
  const pageSize    = filters.page_size ?? 25;
  const totalPages  = Math.ceil(total / pageSize);

  // Debounced search
  const applySearch = useCallback(() => {
    setFilters((f) => ({ ...f, search: searchInput || undefined, page: 1 }));
  }, [searchInput]);

  function setFilter(key: keyof EmployeeFilters, value: string | number | undefined) {
    setFilters((f) => ({ ...f, [key]: value || undefined, page: 1 }));
  }

  return (
    <div className="flex flex-col h-full">
      {/* ── Page header ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-white dark:bg-slate-950 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-hrms-600" />
          <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Employees</h1>
          {total > 0 && (
            <Badge variant="secondary" className="text-xs">{total}</Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline" size="sm"
            onClick={() => exportFn(filters)}
            className="gap-1.5"
          >
            <Download className="h-3.5 w-3.5" />
            Export
          </Button>
          {canCreate && (
            <Button
              size="sm"
              className="bg-hrms-600 hover:bg-hrms-700 text-white gap-1.5"
              onClick={() => router.push('/employees/new')}
            >
              <Plus className="h-4 w-4" />
              Add employee
            </Button>
          )}
        </div>
      </div>

      {/* ── Filters bar ────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 px-6 py-3 bg-slate-50 dark:bg-slate-900/50 border-b">
        {/* Search */}
        <div className="flex gap-1 flex-1 min-w-48 max-w-xs">
          <Input
            placeholder="Search name, email, CNIC…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && applySearch()}
            className="h-8 text-sm"
          />
          <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" onClick={applySearch}>
            <Search className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Department */}
        <Select
          value={filters.department_id || 'all'}
          onValueChange={(v) => setFilter('department_id', v === 'all' ? '' : v)}
        >
          <SelectTrigger className="h-8 text-sm w-44">
            <SelectValue placeholder="All departments" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Departments</SelectItem>
            {departments.map((d) => (
              <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Status */}
        <Select
          value={filters.status || 'all'}
          onValueChange={(v) => setFilter('status', v === 'all' ? '' : v)}
        >
          <SelectTrigger className="h-8 text-sm w-36">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Page size */}
        <Select
          value={String(pageSize)}
          onValueChange={(v) => setFilters((f) => ({ ...f, page_size: Number(v), page: 1 }))}
        >
          <SelectTrigger className="h-8 text-sm w-24">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZES.map((s) => (
              <SelectItem key={s} value={String(s)}>{s} / page</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Clear filters */}
        {(filters.department_id || filters.status || filters.search) && (
          <Button
            variant="ghost" size="sm" className="h-8 text-xs gap-1"
            onClick={() => {
              setFilters({ page: 1, page_size: pageSize });
              setSearchInput('');
            }}
          >
            <Filter className="h-3 w-3" /> Clear
          </Button>
        )}
      </div>

      {/* ── Table ──────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50 dark:bg-slate-900/50">
              <TableHead className="w-64">Employee</TableHead>
              <TableHead>Code</TableHead>
              <TableHead>Department · Designation</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Joined</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <SkeletonRows count={pageSize} />
            ) : employees.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-16 text-slate-400">
                  <Users className="h-10 w-10 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">No employees found.</p>
                  {canCreate && (
                    <Button
                      size="sm" variant="outline" className="mt-3"
                      onClick={() => router.push('/employees/new')}
                    >
                      Add your first employee
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ) : (
              employees.map((emp) => (
                <TableRow
                  key={emp.id}
                  className={`cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 ${isFetching ? 'opacity-60' : ''}`}
                  onClick={() => router.push(`/employees/${emp.id}`)}
                >
                  {/* Name + avatar */}
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <EmployeeAvatar
                        name={emp.full_name}
                        photoUrl={emp.photo_url}
                        size="sm"
                      />
                      <div>
                        <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                          {emp.full_name}
                        </p>
                        <p className="text-xs text-slate-500 truncate max-w-[180px]">
                          {emp.work_email ?? emp.personal_email ?? '—'}
                        </p>
                      </div>
                    </div>
                  </TableCell>

                  {/* Code */}
                  <TableCell>
                    <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                      {emp.employee_code}
                    </span>
                  </TableCell>

                  {/* Dept · Designation */}
                  <TableCell>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {emp.department_name ?? '—'}
                    </p>
                    <p className="text-xs text-slate-400">{emp.designation_title ?? ''}</p>
                  </TableCell>

                  {/* Status */}
                  <TableCell>
                    <EmployeeStatusBadge status={emp.employment_status} />
                  </TableCell>

                  {/* Joined */}
                  <TableCell className="text-sm text-slate-500">
                    {emp.date_of_joining
                      ? new Date(emp.date_of_joining).toLocaleDateString('en-PK', {
                          day: '2-digit', month: 'short', year: 'numeric',
                        })
                      : '—'}
                  </TableCell>

                  {/* Actions */}
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => router.push(`/employees/${emp.id}`)}>
                          View profile
                        </DropdownMenuItem>
                        {canCreate && (
                          <DropdownMenuItem onClick={() => router.push(`/employees/${emp.id}/edit`)}>
                            Edit
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* ── Pagination ─────────────────────────────────────────────── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-3 border-t bg-white dark:bg-slate-950 text-sm text-slate-500">
          <span>
            Showing {Math.min((currentPage - 1) * pageSize + 1, total)}–
            {Math.min(currentPage * pageSize, total)} of {total}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline" size="icon" className="h-7 w-7"
              disabled={currentPage <= 1}
              onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) - 1 }))}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="px-2 text-xs">{currentPage} / {totalPages}</span>
            <Button
              variant="outline" size="icon" className="h-7 w-7"
              disabled={currentPage >= totalPages}
              onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) + 1 }))}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
