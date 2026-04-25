'use client';

import { useState }      from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft, Edit, UserCog, Phone, Mail, MapPin,
  Building2, Briefcase, Calendar, CreditCard,
  FileText, AlertTriangle, Loader2,
} from 'lucide-react';
import { format } from 'date-fns';

import { Button }          from '@/components/ui/button';
import { Badge }           from '@/components/ui/badge';
import { Skeleton }        from '@/components/ui/skeleton';
import { Separator }       from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/components/ui/card';

import { EmployeeAvatar }      from '@/components/employees/EmployeeAvatar';
import { EmployeeStatusBadge } from '@/components/employees/EmployeeStatusBadge';
import { StatusChangeDialog }  from '@/components/employees/StatusChangeDialog';
import { DocumentCard }        from '@/components/employees/DocumentCard';
import { SalaryBreakdownCard } from '@/components/employees/SalaryBreakdownCard';

import {
  useEmployee,
  useEmployeeSalary,
  useUpdateEmployeeStatus,
  useDeleteDocument,
} from '@/hooks/useEmployees';
import { useAuthStore } from '@/stores/authStore';
import type { EmployeeStatus } from '@/types/employee';
import { AttritionRiskCard }        from '@/components/ai/AttritionRiskCard';
import { usePerformancePrediction } from '@/hooks/useAI';

// ─── Field helpers ────────────────────────────────────────────────────────────

function InfoRow({ icon: Icon, label, value }: {
  icon: React.ElementType; label: string; value?: string | null;
}) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      <Icon className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
      <div className="min-w-0">
        <p className="text-[11px] text-slate-400 uppercase tracking-wide">{label}</p>
        <p className="text-sm text-slate-700 dark:text-slate-200 break-words">
          {value ?? <span className="text-slate-400 italic">—</span>}
        </p>
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 mt-4">
      {children}
    </h3>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function ProfileSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-6 animate-pulse">
      <div className="flex items-center gap-4">
        <Skeleton className="w-20 h-20 rounded-full" />
        <div className="space-y-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
      </div>
      {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
    </div>
  );
}

// ─── AI Insights tab ──────────────────────────────────────────────────────────

function PerformanceBandBadge({ band }: { band: string }) {
  const cls =
    band === 'High'   ? 'bg-green-100 text-green-700' :
    band === 'Medium' ? 'bg-amber-100 text-amber-700'  :
    'bg-red-100 text-red-700';
  return <Badge className={`text-xs px-2 ${cls}`}>{band} Performance</Badge>;
}

function AIInsightsTabContent({ employeeId }: { employeeId: string }) {
  const { data: perf, isLoading: perfLoading } = usePerformancePrediction(employeeId);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 max-w-4xl">
      {/* Attrition Risk */}
      <AttritionRiskCard employeeId={employeeId} />

      {/* Performance Prediction */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Performance Prediction</CardTitle>
        </CardHeader>
        <CardContent>
          {perfLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : !perf ? (
            <p className="text-sm text-slate-400 py-4 text-center">
              Unable to load performance prediction.
            </p>
          ) : (
            <div className="space-y-4">
              {/* Score + band */}
              <div className="flex items-center gap-3">
                <div className="text-3xl font-bold text-slate-700">
                  {perf.predicted_score.toFixed(1)}
                  <span className="text-sm font-normal text-slate-400">/5</span>
                </div>
                <div>
                  <PerformanceBandBadge band={perf.predicted_band} />
                  <p className="text-xs text-slate-400 mt-1">
                    Confidence: {(perf.confidence * 100).toFixed(0)}%
                  </p>
                </div>
              </div>

              {/* Key drivers */}
              {perf.key_drivers.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                    Key Drivers
                  </p>
                  <ul className="space-y-1">
                    {perf.key_drivers.map((d, i) => (
                      <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600">
                        <span className="text-hrms-500 mt-0.5">→</span>
                        {d.label ?? d.factor}
                        <span className="text-slate-400 ml-1">({d.direction})</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Improvement suggestions */}
              {perf.improvement_suggestions.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                    Suggestions
                  </p>
                  <ul className="space-y-1">
                    {perf.improvement_suggestions.map((s, i) => (
                      <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600">
                        <span className="text-green-500 mt-0.5">✓</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="text-[10px] text-slate-400">
                Predicted {new Date(perf.predicted_at).toLocaleDateString()}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function EmployeeProfilePage() {
  const { id }  = useParams<{ id: string }>();
  const router  = useRouter();

  const canEdit       = useAuthStore((s) => s.hasPermission('employees', 'update'));
  const canViewSalary = useAuthStore((s) => s.hasPermission('employees', 'view_salary') || s.user?.id === id);
  const canDelete     = useAuthStore((s) => s.hasPermission('employees', 'delete'));
  const canViewAI     = useAuthStore((s) => s.hasPermission('employees', 'read'));

  const { data: emp, isLoading, isError } = useEmployee(id);
  const { data: salaryData }              = useEmployeeSalary(id);

  const statusMutation = useUpdateEmployeeStatus(id);
  const deleteMutation = useDeleteDocument(id);

  const [statusDialogOpen, setStatusDialogOpen] = useState(false);

  // ── Error / loading ────────────────────────────────────────────
  if (isLoading) return <ProfileSkeleton />;

  if (isError || !emp) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400">
        <AlertTriangle className="h-12 w-12 mb-3 opacity-40" />
        <p className="text-sm mb-3">Employee not found or you don't have access.</p>
        <Button variant="outline" size="sm" onClick={() => router.back()}>Go back</Button>
      </div>
    );
  }

  // ── Derived values ─────────────────────────────────────────────
  const fullAddress = [
    emp.address_line1,
    emp.address_line2,
    emp.city,
    emp.state,
    emp.country,
  ].filter(Boolean).join(', ');

  async function handleStatusChange(status: EmployeeStatus, reason?: string) {
    await statusMutation.mutateAsync({ employment_status: status, reason });
  }

  return (
    <div className="flex flex-col h-full">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between px-6 py-4 border-b bg-white dark:bg-slate-950 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <EmployeeAvatar name={emp.full_name} photoUrl={emp.photo_url} size="lg" />
          <div>
            <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100 leading-tight">
              {emp.full_name}
            </h1>
            <p className="text-sm text-slate-500">
              {emp.designation_title ?? ''}{emp.department_name ? ` · ${emp.department_name}` : ''}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <EmployeeStatusBadge status={emp.employment_status} />
              <span className="font-mono text-xs text-slate-400">{emp.employee_code}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {canEdit && (
            <>
              <Button
                variant="outline" size="sm" className="gap-1.5"
                onClick={() => setStatusDialogOpen(true)}
              >
                <UserCog className="h-3.5 w-3.5" />
                Change status
              </Button>
              <Button
                size="sm"
                className="bg-hrms-600 hover:bg-hrms-700 text-white gap-1.5"
                onClick={() => router.push(`/employees/${id}/edit`)}
              >
                <Edit className="h-3.5 w-3.5" />
                Edit
              </Button>
            </>
          )}
        </div>
      </div>

      {/* ── Tabs ──────────────────────────────────────────────────── */}
      <Tabs defaultValue="overview" className="flex-1 overflow-hidden flex flex-col">
        <div className="border-b bg-white dark:bg-slate-950 px-6">
          <TabsList className="h-10 bg-transparent gap-1 p-0">
            {[
              { value: 'overview',   label: 'Overview' },
              { value: 'personal',   label: 'Personal' },
              { value: 'employment', label: 'Employment' },
              { value: 'salary',     label: 'Salary',    hidden: !canViewSalary },
              { value: 'documents',  label: 'Documents' },
              { value: 'leave',      label: 'Leave' },
              { value: 'attendance', label: 'Attendance' },
              { value: 'history',    label: 'History' },
              { value: 'ai',         label: 'AI Insights', hidden: !canViewAI },
            ].filter((t) => !t.hidden).map((t) => (
              <TabsTrigger
                key={t.value} value={t.value}
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-hrms-600 data-[state=active]:text-hrms-700 dark:data-[state=active]:text-hrms-400 h-10 px-3 text-sm"
              >
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <div className="flex-1 overflow-auto p-6">

          {/* ── Overview ──────────────────────────────────────────── */}
          <TabsContent value="overview" className="mt-0">
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {/* Quick info */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Contact</CardTitle></CardHeader>
                <CardContent className="space-y-0 divide-y dark:divide-slate-800">
                  <InfoRow icon={Mail}  label="Work email"     value={emp.work_email} />
                  <InfoRow icon={Mail}  label="Personal email" value={emp.personal_email} />
                  <InfoRow icon={Phone} label="Phone"          value={emp.phone_number} />
                  <InfoRow icon={MapPin}label="Address"        value={fullAddress || null} />
                </CardContent>
              </Card>

              {/* Employment */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Employment</CardTitle></CardHeader>
                <CardContent className="space-y-0 divide-y dark:divide-slate-800">
                  <InfoRow icon={Building2} label="Department"   value={emp.department_name} />
                  <InfoRow icon={Briefcase} label="Designation"  value={emp.designation_title} />
                  <InfoRow icon={CreditCard}label="Contract"     value={emp.contract_type} />
                  <InfoRow icon={Calendar}  label="Joined"
                    value={emp.date_of_joining
                      ? format(new Date(emp.date_of_joining), 'dd MMM yyyy')
                      : undefined} />
                </CardContent>
              </Card>

              {/* Manager */}
              {emp.manager_id && (
                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-sm">Reporting</CardTitle></CardHeader>
                  <CardContent>
                    <button
                      onClick={() => router.push(`/employees/${emp.manager_id}`)}
                      className="flex items-center gap-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg p-2 -m-2 transition-colors w-full"
                    >
                      <EmployeeAvatar name={emp.manager_name ?? 'Manager'} size="sm" />
                      <div>
                        <p className="text-sm font-medium text-hrms-600 hover:underline">
                          {emp.manager_name ?? 'View manager'}
                        </p>
                        <p className="text-xs text-slate-400">Direct manager</p>
                      </div>
                    </button>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* ── Personal ──────────────────────────────────────────── */}
          <TabsContent value="personal" className="mt-0 max-w-2xl">
            <Card>
              <CardContent className="pt-4 divide-y dark:divide-slate-800">
                <SectionTitle>Identity</SectionTitle>
                <InfoRow icon={CreditCard} label="CNIC"        value={emp.cnic} />
                <InfoRow icon={FileText}   label="Passport"    value={emp.passport_number} />
                <InfoRow icon={Calendar}   label="Date of birth"
                  value={emp.date_of_birth
                    ? format(new Date(emp.date_of_birth), 'dd MMM yyyy')
                    : undefined} />
                <InfoRow icon={Briefcase}  label="Gender"      value={emp.gender} />
                <InfoRow icon={Briefcase}  label="Nationality" value={emp.nationality} />
                <InfoRow icon={Briefcase}  label="Blood group" value={emp.blood_group} />
                <SectionTitle>Emergency Contact</SectionTitle>
                <InfoRow icon={Phone} label="Name"         value={emp.emergency_contact_name} />
                <InfoRow icon={Phone} label="Phone"        value={emp.emergency_contact_phone} />
                <InfoRow icon={Briefcase} label="Relation" value={emp.emergency_contact_relation} />
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Employment ────────────────────────────────────────── */}
          <TabsContent value="employment" className="mt-0 max-w-2xl">
            <Card>
              <CardContent className="pt-4 divide-y dark:divide-slate-800">
                <InfoRow icon={Building2} label="Department"    value={emp.department_name} />
                <InfoRow icon={Briefcase} label="Designation"   value={emp.designation_title} />
                <InfoRow icon={CreditCard}label="Contract type" value={emp.contract_type} />
                <InfoRow icon={Calendar}  label="Date of joining"
                  value={emp.date_of_joining
                    ? format(new Date(emp.date_of_joining), 'dd MMM yyyy')
                    : undefined} />
                <InfoRow icon={Calendar}  label="Probation end"
                  value={emp.probation_end_date
                    ? format(new Date(emp.probation_end_date), 'dd MMM yyyy')
                    : undefined} />
                <InfoRow icon={Calendar}  label="Contract end"
                  value={emp.contract_end_date
                    ? format(new Date(emp.contract_end_date), 'dd MMM yyyy')
                    : undefined} />
                <InfoRow icon={Mail}      label="Work email"    value={emp.work_email} />
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Salary ────────────────────────────────────────────── */}
          {canViewSalary && (
            <TabsContent value="salary" className="mt-0 max-w-md">
              {salaryData?.current_salary ? (
                <SalaryBreakdownCard salary={salaryData.current_salary} />
              ) : (
                <div className="text-center py-12 text-slate-400">
                  <p className="text-sm">No salary structure found.</p>
                </div>
              )}
            </TabsContent>
          )}

          {/* ── Documents ─────────────────────────────────────────── */}
          <TabsContent value="documents" className="mt-0">
            {emp.documents && emp.documents.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-3xl">
                {emp.documents.map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    document={doc}
                    canDelete={canDelete}
                    isDeleting={deleteMutation.isPending}
                    onDownload={(d) => { if (d.file_url) window.open(d.file_url, '_blank'); }}
                    onDelete={(docId) => deleteMutation.mutate(docId)}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400">
                <FileText className="h-10 w-10 mx-auto mb-3 opacity-30" />
                <p className="text-sm">No documents uploaded.</p>
              </div>
            )}
          </TabsContent>

          {/* ── Leave ─────────────────────────────────────────────── */}
          <TabsContent value="leave" className="mt-0">
            {emp.leave_balances && emp.leave_balances.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-3 max-w-3xl">
                {emp.leave_balances.map((lb) => (
                  <Card key={lb.leave_type_id} className="text-center p-4">
                    <p className="text-xs text-slate-500 mb-1">{lb.leave_type_name}</p>
                    <p className="text-3xl font-bold text-hrms-600">{lb.remaining}</p>
                    <p className="text-[11px] text-slate-400">
                      {lb.used} used / {lb.total} total
                    </p>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400">
                <p className="text-sm">No leave balance data.</p>
              </div>
            )}
          </TabsContent>

          {/* ── Attendance ────────────────────────────────────────── */}
          <TabsContent value="attendance" className="mt-0">
            {emp.attendance_summary ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-xl">
                {[
                  { label: 'Present',  value: emp.attendance_summary.present_days,  color: 'text-green-600' },
                  { label: 'Absent',   value: emp.attendance_summary.absent_days,   color: 'text-red-600' },
                  { label: 'Late',     value: emp.attendance_summary.late_days,     color: 'text-yellow-600' },
                  { label: 'On Leave', value: emp.attendance_summary.leave_days,    color: 'text-purple-600' },
                ].map(({ label, value, color }) => (
                  <Card key={label} className="text-center p-4">
                    <p className="text-xs text-slate-500 mb-1">{label}</p>
                    <p className={`text-3xl font-bold ${color}`}>{value ?? 0}</p>
                    <p className="text-[11px] text-slate-400">days</p>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400">
                <p className="text-sm">No attendance data for this period.</p>
              </div>
            )}
          </TabsContent>

          {/* ── History ───────────────────────────────────────────── */}
          <TabsContent value="history" className="mt-0 max-w-2xl">
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-slate-400">
                  Created {emp.created_at ? format(new Date(emp.created_at), 'dd MMM yyyy, HH:mm') : '—'}
                </p>
                {emp.updated_at !== emp.created_at && (
                  <p className="text-xs text-slate-400 mt-1">
                    Last updated {emp.updated_at ? format(new Date(emp.updated_at), 'dd MMM yyyy, HH:mm') : '—'}
                  </p>
                )}
                <Separator className="my-4" />
                {salaryData?.salary_history && salaryData.salary_history.length > 0 ? (
                  <div className="space-y-3">
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Salary history</p>
                    {salaryData.salary_history.map((s) => (
                      <div key={s.id} className="flex items-start justify-between text-sm py-2 border-b dark:border-slate-800 last:border-0">
                        <div>
                          <p className="text-slate-700 dark:text-slate-200 font-medium">
                            {new Intl.NumberFormat('en-PK', { style: 'currency', currency: 'PKR', maximumFractionDigits: 0 }).format(s.basic_salary)}
                            {' '}<span className="text-slate-400 font-normal text-xs">basic</span>
                          </p>
                          {s.revision_note && (
                            <p className="text-xs text-slate-400 mt-0.5">{s.revision_note}</p>
                          )}
                        </div>
                        <span className="text-xs text-slate-400 shrink-0 ml-4">
                          {format(new Date(s.effective_from), 'dd MMM yyyy')}
                          {s.effective_to
                            ? ` → ${format(new Date(s.effective_to), 'dd MMM yyyy')}`
                            : ' → present'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">No salary history available.</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── AI Insights ───────────────────────────────────────── */}
          {canViewAI && (
            <TabsContent value="ai" className="mt-0">
              <AIInsightsTabContent employeeId={id} />
            </TabsContent>
          )}

        </div>
      </Tabs>

      {/* ── Status change dialog ──────────────────────────────────── */}
      <StatusChangeDialog
        open={statusDialogOpen}
        onOpenChange={setStatusDialogOpen}
        currentStatus={emp.employment_status}
        employeeName={emp.full_name}
        onConfirm={handleStatusChange}
        isPending={statusMutation.isPending}
      />
    </div>
  );
}
