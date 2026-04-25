'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Play, Eye, CheckCircle2, XCircle, Download,
  FileText, Settings, Users, Loader2, RefreshCw,
} from 'lucide-react';
import { format } from 'date-fns';

import { Button }   from '@/components/ui/button';
import { Badge }    from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { Input }    from '@/components/ui/input';
import { Label }    from '@/components/ui/label';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/components/ui/card';

import { RunPayrollDialog }       from '@/components/payroll/RunPayrollDialog';
import { PayrollApprovalDialog }  from '@/components/payroll/PayrollApprovalDialog';
import { PayrollSummaryCards }    from '@/components/payroll/PayrollSummaryCards';
import { PayslipCard }            from '@/components/payroll/PayslipCard';
import { TaxCalculatorWidget }    from '@/components/payroll/TaxCalculatorWidget';

import {
  usePayrollRuns,
  usePayrollRun,
  useMyPayslips,
  useTaxSlabs,
  useUpdateTaxSlab,
  useCreateTaxSlab,
} from '@/hooks/usePayroll';
import { useAuthStore }     from '@/stores/authStore';
import { getBankFileUrl, getPayslipPdfUrl } from '@/lib/api/payroll';
import type { PayrollRun, PayrollRecord, PayrollRunStatus, TaxSlab } from '@/types/payroll';

// ─── Constants ────────────────────────────────────────────────────────────────

const MONTHS = [
  'Jan','Feb','Mar','Apr','May','Jun',
  'Jul','Aug','Sep','Oct','Nov','Dec',
];

function getCurrentYear() { return new Date().getFullYear(); }
function getYearOptions() {
  const y = getCurrentYear();
  return Array.from({ length: 4 }, (_, i) => y - i);
}

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<PayrollRunStatus, string> = {
  draft:      'bg-slate-100 text-slate-500 border-slate-200',
  processing: 'bg-blue-100 text-blue-700 border-blue-200',
  processed:  'bg-amber-100 text-amber-700 border-amber-200',
  approved:   'bg-green-100 text-green-700 border-green-200',
  paid:       'bg-emerald-100 text-emerald-700 border-emerald-200',
  cancelled:  'bg-red-100 text-red-600 border-red-200',
  rejected:   'bg-red-100 text-red-600 border-red-200',
};

function StatusBadge({ status }: { status: PayrollRunStatus }) {
  return (
    <Badge variant="outline" className={STATUS_STYLES[status] + ' text-xs capitalize'}>
      {status === 'processing' && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
      {status}
    </Badge>
  );
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 }).format(n);
}

// ─── Tab 1: Payroll Runs ──────────────────────────────────────────────────────

function PayrollRunsTab() {
  const [runDialogOpen, setRunDialogOpen]     = useState(false);
  const [filterYear,    setFilterYear]        = useState<number>(getCurrentYear);
  const [selectedRunId, setSelectedRunId]     = useState<string | null>(null);
  const [approval, setApproval]              = useState<{
    open: boolean; action: 'approve' | 'reject'; run: PayrollRun;
  } | null>(null);

  const { data, isLoading } = usePayrollRuns({ year: filterYear });
  const runs = data?.results ?? [];

  // Find active processing run for banner
  const processingRun = runs.find((r) => r.status === 'processing');

  // Auto-refresh every 5s while a run is processing
  const { data: activeRunData } = usePayrollRun(
    processingRun?.id ?? '',
    { enabled: !!processingRun, refetchInterval: processingRun ? 5_000 : undefined },
  );

  const handleDownloadBankFile = (runId: string) => {
    window.open(getBankFileUrl(runId), '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Payroll Runs</h2>
          <p className="text-sm text-slate-500 mt-0.5">Monthly payroll processing history</p>
        </div>
        <Button
          onClick={() => setRunDialogOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 gap-2"
        >
          <Play className="h-4 w-4" />
          Run Payroll
        </Button>
      </div>

      {/* Processing banner */}
      {processingRun && (
        <div className="flex items-center gap-4 rounded-xl border border-blue-200 bg-blue-50 p-4">
          <Loader2 className="h-5 w-5 text-blue-600 animate-spin shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-blue-800 text-sm">
              {MONTHS[processingRun.month - 1]} {processingRun.year} payroll is processing…
            </p>
            <div className="mt-1.5">
              <Progress
                value={
                  activeRunData?.total_employees
                    ? Math.min(100, (activeRunData.total_employees / (activeRunData.total_employees || 1)) * 100)
                    : 20
                }
                className="h-1.5"
              />
            </div>
            {(activeRunData?.total_employees ?? 0) > 0 && (
              <p className="text-xs text-blue-600 mt-1">
                {activeRunData?.total_employees ?? 0} employees processed
              </p>
            )}
          </div>
          <Badge variant="outline" className="border-blue-300 text-blue-700 shrink-0">
            Live
          </Badge>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Label className="text-sm shrink-0">Year:</Label>
        <Select value={String(filterYear)} onValueChange={(v) => setFilterYear(Number(v))}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {getYearOptions().map((y) => (
              <SelectItem key={y} value={String(y)}>{y}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-sm text-slate-500">{runs.length} runs</span>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded" />
          ))}
        </div>
      ) : runs.length === 0 ? (
        <div className="py-16 text-center text-slate-500">
          <FileText className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium">No payroll runs for {filterYear}</p>
          <p className="text-sm mt-1">Click &ldquo;Run Payroll&rdquo; to start the first run.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50">
                <TableHead>Month / Year</TableHead>
                <TableHead className="text-right">Employees</TableHead>
                <TableHead className="text-right">Gross (PKR)</TableHead>
                <TableHead className="text-right">Deductions (PKR)</TableHead>
                <TableHead className="text-right">Net (PKR)</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => (
                <TableRow key={run.id} className="hover:bg-slate-50">
                  <TableCell className="font-medium">
                    {MONTHS[run.month - 1]} {run.year}
                  </TableCell>
                  <TableCell className="text-right">{run.total_employees}</TableCell>
                  <TableCell className="text-right">{fmt(run.total_gross)}</TableCell>
                  <TableCell className="text-right text-red-600">{fmt(run.total_deductions)}</TableCell>
                  <TableCell className="text-right font-semibold text-green-700">
                    {fmt(run.total_net)}
                  </TableCell>
                  <TableCell><StatusBadge status={run.status} /></TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedRunId(run.id)}
                        title="View details"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      {run.status === 'processed' && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-green-600 hover:text-green-700"
                            onClick={() => setApproval({ open: true, action: 'approve', run })}
                            title="Approve"
                          >
                            <CheckCircle2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-600"
                            onClick={() => setApproval({ open: true, action: 'reject', run })}
                            title="Reject"
                          >
                            <XCircle className="h-4 w-4" />
                          </Button>
                        </>
                      )}
                      {(run.status === 'approved' || run.status === 'paid') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownloadBankFile(run.id)}
                          title="Download bank file"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Dialogs */}
      <RunPayrollDialog open={runDialogOpen} onClose={() => setRunDialogOpen(false)} />

      {approval && (
        <PayrollApprovalDialog
          open={approval.open}
          action={approval.action}
          run={approval.run}
          onClose={() => setApproval(null)}
        />
      )}

      {/* Run detail drawer / tab change */}
      {selectedRunId && (
        <RunDetailPanel
          runId={selectedRunId}
          onClose={() => setSelectedRunId(null)}
          onApprove={(run) => setApproval({ open: true, action: 'approve', run })}
          onReject={(run)  => setApproval({ open: true, action: 'reject',  run })}
        />
      )}
    </div>
  );
}

// ─── Run Detail Panel ─────────────────────────────────────────────────────────

function RunDetailPanel({
  runId, onClose, onApprove, onReject,
}: {
  runId: string;
  onClose:   () => void;
  onApprove: (run: PayrollRun) => void;
  onReject:  (run: PayrollRun) => void;
}) {
  const [search, setSearch] = useState('');
  const { data: run, isLoading } = usePayrollRun(runId, {
    refetchInterval: runId ? 5_000 : undefined,
  } as any);

  if (isLoading) return (
    <div className="space-y-3 mt-4">
      {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-10" />)}
    </div>
  );
  if (!run) return null;

  const filtered = (run.records ?? []).filter((r) =>
    r.employee?.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    r.employee?.employee_code?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="mt-2 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">
          {MONTHS[run.month - 1]} {run.year} — Detail
          <StatusBadge status={run.status} />
        </h3>
        <Button variant="outline" size="sm" onClick={onClose}>Close</Button>
      </div>

      <PayrollSummaryCards current={run} />

      <div className="flex items-center gap-3">
        <Input
          placeholder="Search employee…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <span className="text-sm text-slate-500">{filtered.length} records</span>

        {run.status === 'processed' && (
          <div className="ml-auto flex gap-2">
            <Button
              size="sm"
              className="bg-green-600 hover:bg-green-700 text-white"
              onClick={() => onApprove(run)}
            >
              <CheckCircle2 className="h-4 w-4 mr-1" /> Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => onReject(run)}
            >
              <XCircle className="h-4 w-4 mr-1" /> Reject
            </Button>
          </div>
        )}
        {(run.status === 'approved' || run.status === 'paid') && (
          <Button
            size="sm"
            variant="outline"
            className="ml-auto"
            onClick={() => window.open(getBankFileUrl(run.id), '_blank')}
          >
            <Download className="h-4 w-4 mr-1" /> Bank File
          </Button>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50">
              <TableHead>Employee</TableHead>
              <TableHead className="text-right">Basic</TableHead>
              <TableHead className="text-right">Allowances</TableHead>
              <TableHead className="text-right">Gross</TableHead>
              <TableHead className="text-right">EOBI</TableHead>
              <TableHead className="text-right">Tax</TableHead>
              <TableHead className="text-right">Deductions</TableHead>
              <TableHead className="text-right font-semibold">Net</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((record) => (
              <TableRow key={record.id} className="hover:bg-slate-50 text-sm">
                <TableCell>
                  <div>
                    <p className="font-medium text-slate-800">{record.employee?.full_name}</p>
                    <p className="text-xs text-slate-500">{record.employee?.employee_code}</p>
                  </div>
                </TableCell>
                <TableCell className="text-right">{fmt(record.basic_salary)}</TableCell>
                <TableCell className="text-right">{fmt(record.total_allowances)}</TableCell>
                <TableCell className="text-right">{fmt(record.gross_salary)}</TableCell>
                <TableCell className="text-right text-slate-500">{fmt(record.eobi_employee)}</TableCell>
                <TableCell className="text-right text-slate-500">{fmt(record.income_tax)}</TableCell>
                <TableCell className="text-right text-red-600">{fmt(record.total_deductions)}</TableCell>
                <TableCell className="text-right font-semibold text-green-700">
                  {fmt(record.net_salary)}
                </TableCell>
                <TableCell>
                  {record.payslip_url && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(getPayslipPdfUrl(record.id), '_blank')}
                    >
                      <FileText className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-slate-500">
                  No records found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ─── Tab 2: My Payslips ───────────────────────────────────────────────────────

function MyPayslipsTab() {
  const { data: records = [], isLoading } = useMyPayslips();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">My Payslips</h2>
        <p className="text-sm text-slate-500 mt-0.5">Your salary history</p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      ) : records.length === 0 ? (
        <div className="py-20 text-center text-slate-500">
          <FileText className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium">No payslips yet</p>
          <p className="text-sm mt-1">Your salary slips will appear here once payroll is processed.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {records.map((record) => (
            <PayslipCard key={record.id} record={record} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Tab 3: Tax & Settings ────────────────────────────────────────────────────

function TaxSettingsTab() {
  const [selectedYear, setSelectedYear] = useState(getCurrentYear);
  const { data: slabs = [], isLoading } = useTaxSlabs(selectedYear);
  const updateSlab = useUpdateTaxSlab(selectedYear);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Tax & Settings</h2>
          <p className="text-sm text-slate-500 mt-0.5">FBR income tax slabs and payroll configuration</p>
        </div>
        <Select value={String(selectedYear)} onValueChange={(v) => setSelectedYear(Number(v))}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {getYearOptions().map((y) => (
              <SelectItem key={y} value={String(y)}>{y}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <TaxCalculatorWidget year={selectedYear} />

      {/* Custom Slabs */}
      {slabs.length > 0 && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-slate-700">
              Custom Tax Slabs ({selectedYear})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead>Min Income</TableHead>
                  <TableHead>Max Income</TableHead>
                  <TableHead>Fixed Tax</TableHead>
                  <TableHead>Rate</TableHead>
                  <TableHead>Active</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Skeleton className="h-8 w-full" />
                    </TableCell>
                  </TableRow>
                ) : slabs.map((slab) => (
                  <TableRow key={slab.id}>
                    <TableCell>PKR {fmt(slab.min_income)}</TableCell>
                    <TableCell>{slab.max_income ? `PKR ${fmt(slab.max_income)}` : 'No limit'}</TableCell>
                    <TableCell>PKR {fmt(slab.fixed_tax)}</TableCell>
                    <TableCell>{(slab.tax_rate * 100).toFixed(1)}%</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={slab.is_active
                          ? 'border-green-200 text-green-700 bg-green-50'
                          : 'border-slate-200 text-slate-400 bg-slate-50'
                        }
                      >
                        {slab.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PayrollPage() {
  const user    = useAuthStore((s) => s.user);
  const isHR    = user?.is_superadmin || false;  // simplified; extend with RBAC as needed

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Payroll</h1>
        <p className="text-sm text-slate-500 mt-1">
          Manage monthly payroll runs, payslips, and tax configuration.
        </p>
      </div>

      <Tabs defaultValue={isHR ? 'runs' : 'payslips'} className="space-y-6">
        <TabsList className="bg-slate-100 p-1 rounded-lg">
          {isHR && (
            <TabsTrigger value="runs" className="gap-2 rounded-md">
              <Play className="h-4 w-4" />
              Payroll Runs
            </TabsTrigger>
          )}
          <TabsTrigger value="payslips" className="gap-2 rounded-md">
            <FileText className="h-4 w-4" />
            My Payslips
          </TabsTrigger>
          {isHR && (
            <TabsTrigger value="tax" className="gap-2 rounded-md">
              <Settings className="h-4 w-4" />
              Tax &amp; Settings
            </TabsTrigger>
          )}
        </TabsList>

        {isHR && (
          <TabsContent value="runs">
            <PayrollRunsTab />
          </TabsContent>
        )}

        <TabsContent value="payslips">
          <MyPayslipsTab />
        </TabsContent>

        {isHR && (
          <TabsContent value="tax">
            <TaxSettingsTab />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
