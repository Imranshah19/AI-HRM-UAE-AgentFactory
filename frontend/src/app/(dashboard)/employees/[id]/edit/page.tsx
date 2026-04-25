'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useForm, Controller }  from 'react-hook-form';
import { zodResolver }          from '@hookform/resolvers/zod';
import { z }                    from 'zod';
import { ArrowLeft, Save, Loader2, AlertTriangle } from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Input }    from '@/components/ui/input';
import { Label }    from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Skeleton }  from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import {
  useEmployee, useUpdateEmployee, useDepartments, useDesignations,
} from '@/hooks/useEmployees';
import type { EmployeeUpdateData } from '@/types/employee';

// ─── Schema ───────────────────────────────────────────────────────────────────

const schema = z.object({
  // Personal
  first_name:                 z.string().min(1),
  last_name:                  z.string().min(1),
  middle_name:                z.string().optional(),
  gender:                     z.string().optional(),
  date_of_birth:              z.string().optional(),
  nationality:                z.string().optional(),
  blood_group:                z.string().optional(),
  cnic:                       z.string().optional(),
  passport_number:            z.string().optional(),
  personal_email:             z.string().email().optional().or(z.literal('')),
  phone_number:               z.string().optional(),
  // Address
  address_line1:              z.string().optional(),
  address_line2:              z.string().optional(),
  city:                       z.string().optional(),
  state:                      z.string().optional(),
  country:                    z.string().optional(),
  postal_code:                z.string().optional(),
  // Employment
  department_id:              z.string().optional(),
  designation_id:             z.string().optional(),
  contract_type:              z.string().optional(),
  date_of_joining:            z.string().optional(),
  probation_end_date:         z.string().optional(),
  contract_end_date:          z.string().optional(),
  manager_id:                 z.string().optional(),
  // Emergency contact
  emergency_contact_name:     z.string().optional(),
  emergency_contact_phone:    z.string().optional(),
  emergency_contact_relation: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function Field({ label, error, required, children }: {
  label: string; error?: string; required?: boolean; children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </Label>
      {children}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function EditEmployeePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: emp, isLoading, isError } = useEmployee(id);
  const { data: departments = [] }        = useDepartments();
  const updateMutation                    = useUpdateEmployee(id);

  const [selectedDept, setSelectedDept]   = useState<string | undefined>();
  const { data: designations = [] }       = useDesignations(selectedDept);

  const {
    register, handleSubmit, reset, control,
    formState: { errors, isDirty },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  // Pre-populate form once employee data is loaded
  useEffect(() => {
    if (!emp) return;
    setSelectedDept(emp.department_id ?? undefined);
    reset({
      first_name:                 emp.first_name,
      last_name:                  emp.last_name,
      middle_name:                emp.middle_name  ?? '',
      gender:                     emp.gender       ?? '',
      date_of_birth:              emp.date_of_birth ?? '',
      nationality:                emp.nationality  ?? '',
      blood_group:                emp.blood_group  ?? '',
      cnic:                       emp.cnic         ?? '',
      passport_number:            emp.passport_number ?? '',
      personal_email:             emp.personal_email ?? '',
      phone_number:               emp.phone_number ?? '',
      address_line1:              emp.address_line1 ?? '',
      address_line2:              emp.address_line2 ?? '',
      city:                       emp.city         ?? '',
      state:                      emp.state        ?? '',
      country:                    emp.country      ?? '',
      postal_code:                emp.postal_code  ?? '',
      department_id:              emp.department_id ?? '',
      designation_id:             emp.designation_id ?? '',
      contract_type:              emp.contract_type ?? '',
      date_of_joining:            emp.date_of_joining ?? '',
      probation_end_date:         emp.probation_end_date ?? '',
      contract_end_date:          emp.contract_end_date ?? '',
      emergency_contact_name:     emp.emergency_contact_name ?? '',
      emergency_contact_phone:    emp.emergency_contact_phone ?? '',
      emergency_contact_relation: emp.emergency_contact_relation ?? '',
    });
  }, [emp, reset]);

  async function onSubmit(data: FormData) {
    // Strip empty strings → undefined for optional fields
    const payload: EmployeeUpdateData = Object.fromEntries(
      Object.entries(data).map(([k, v]) => [k, v === '' ? undefined : v]),
    ) as EmployeeUpdateData;
    await updateMutation.mutateAsync(payload);
    router.push(`/employees/${id}`);
  }

  // ── Error / loading ──────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="p-6 space-y-4 animate-pulse max-w-3xl">
        <Skeleton className="h-8 w-64" />
        {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
      </div>
    );
  }

  if (isError || !emp) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400">
        <AlertTriangle className="h-12 w-12 mb-3 opacity-40" />
        <p className="text-sm mb-3">Employee not found.</p>
        <Button variant="outline" size="sm" onClick={() => router.back()}>Go back</Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-white dark:bg-slate-950 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
              Edit Employee
            </h1>
            <p className="text-xs text-slate-400">{emp.full_name} · {emp.employee_code}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => router.back()} disabled={updateMutation.isPending}>
            Cancel
          </Button>
          <Button
            form="edit-employee-form"
            type="submit"
            size="sm"
            className="bg-hrms-600 hover:bg-hrms-700 text-white gap-1.5"
            disabled={!isDirty || updateMutation.isPending}
          >
            {updateMutation.isPending
              ? <><Loader2 className="h-3.5 w-3.5 animate-spin" />Saving…</>
              : <><Save className="h-3.5 w-3.5" />Save changes</>
            }
          </Button>
        </div>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-auto p-6">
        <form id="edit-employee-form" onSubmit={handleSubmit(onSubmit)}>
          <Tabs defaultValue="personal" className="space-y-4">
            <TabsList>
              <TabsTrigger value="personal">Personal</TabsTrigger>
              <TabsTrigger value="address">Address</TabsTrigger>
              <TabsTrigger value="employment">Employment</TabsTrigger>
              <TabsTrigger value="emergency">Emergency</TabsTrigger>
            </TabsList>

            {/* ── Personal ──────────────────────────────────────── */}
            <TabsContent value="personal">
              <Card>
                <CardHeader><CardTitle className="text-sm">Personal Information</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="First name" required error={errors.first_name?.message}>
                    <Input {...register('first_name')} className={errors.first_name ? 'border-red-400' : ''} />
                  </Field>
                  <Field label="Middle name" error={errors.middle_name?.message}>
                    <Input {...register('middle_name')} />
                  </Field>
                  <Field label="Last name" required error={errors.last_name?.message}>
                    <Input {...register('last_name')} className={errors.last_name ? 'border-red-400' : ''} />
                  </Field>
                  <Field label="Gender">
                    <Controller control={control} name="gender" render={({ field }) => (
                      <Select onValueChange={field.onChange} value={field.value ?? ''}>
                        <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                        <SelectContent>
                          {['male','female','other','prefer_not_to_say'].map((g) => (
                            <SelectItem key={g} value={g}>{g.replace('_', ' ')}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )} />
                  </Field>
                  <Field label="Date of birth">
                    <Input type="date" {...register('date_of_birth')} />
                  </Field>
                  <Field label="CNIC">
                    <Input {...register('cnic')} placeholder="42101-1234567-1" />
                  </Field>
                  <Field label="Passport number">
                    <Input {...register('passport_number')} />
                  </Field>
                  <Field label="Nationality">
                    <Input {...register('nationality')} />
                  </Field>
                  <Field label="Blood group">
                    <Controller control={control} name="blood_group" render={({ field }) => (
                      <Select onValueChange={field.onChange} value={field.value ?? ''}>
                        <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                        <SelectContent>
                          {['A+','A-','B+','B-','O+','O-','AB+','AB-'].map((bg) => (
                            <SelectItem key={bg} value={bg}>{bg}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )} />
                  </Field>
                  <Field label="Personal email" error={errors.personal_email?.message}>
                    <Input type="email" {...register('personal_email')} />
                  </Field>
                  <Field label="Phone number">
                    <Input {...register('phone_number')} />
                  </Field>
                </CardContent>
              </Card>
            </TabsContent>

            {/* ── Address ───────────────────────────────────────── */}
            <TabsContent value="address">
              <Card>
                <CardHeader><CardTitle className="text-sm">Address</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="sm:col-span-2">
                    <Field label="Address line 1">
                      <Input {...register('address_line1')} />
                    </Field>
                  </div>
                  <div className="sm:col-span-2">
                    <Field label="Address line 2">
                      <Input {...register('address_line2')} />
                    </Field>
                  </div>
                  <Field label="City">
                    <Input {...register('city')} />
                  </Field>
                  <Field label="State / Province">
                    <Input {...register('state')} />
                  </Field>
                  <Field label="Country">
                    <Input {...register('country')} />
                  </Field>
                  <Field label="Postal code">
                    <Input {...register('postal_code')} />
                  </Field>
                </CardContent>
              </Card>
            </TabsContent>

            {/* ── Employment ────────────────────────────────────── */}
            <TabsContent value="employment">
              <Card>
                <CardHeader><CardTitle className="text-sm">Employment Details</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Department">
                    <Controller control={control} name="department_id" render={({ field }) => (
                      <Select
                        onValueChange={(v) => { field.onChange(v); setSelectedDept(v); }}
                        value={field.value ?? ''}
                      >
                        <SelectTrigger><SelectValue placeholder="Select department…" /></SelectTrigger>
                        <SelectContent>
                          {departments.map((d) => (
                            <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )} />
                  </Field>
                  <Field label="Designation">
                    <Controller control={control} name="designation_id" render={({ field }) => (
                      <Select onValueChange={field.onChange} value={field.value ?? ''}>
                        <SelectTrigger><SelectValue placeholder="Select designation…" /></SelectTrigger>
                        <SelectContent>
                          {designations.map((d) => (
                            <SelectItem key={d.id} value={d.id}>{d.title}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )} />
                  </Field>
                  <Field label="Contract type">
                    <Controller control={control} name="contract_type" render={({ field }) => (
                      <Select onValueChange={field.onChange} value={field.value ?? ''}>
                        <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                        <SelectContent>
                          {['permanent','contract','probation','internship','part_time','consultant'].map((ct) => (
                            <SelectItem key={ct} value={ct}>{ct.replace('_', ' ')}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )} />
                  </Field>
                  <Field label="Date of joining">
                    <Input type="date" {...register('date_of_joining')} />
                  </Field>
                  <Field label="Probation end date">
                    <Input type="date" {...register('probation_end_date')} />
                  </Field>
                  <Field label="Contract end date">
                    <Input type="date" {...register('contract_end_date')} />
                  </Field>
                </CardContent>
              </Card>
            </TabsContent>

            {/* ── Emergency contact ─────────────────────────────── */}
            <TabsContent value="emergency">
              <Card>
                <CardHeader><CardTitle className="text-sm">Emergency Contact</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Name">
                    <Input {...register('emergency_contact_name')} />
                  </Field>
                  <Field label="Phone">
                    <Input {...register('emergency_contact_phone')} />
                  </Field>
                  <Field label="Relation">
                    <Input {...register('emergency_contact_relation')} placeholder="e.g. Spouse, Parent" />
                  </Field>
                </CardContent>
              </Card>
            </TabsContent>

          </Tabs>
        </form>
      </div>
    </div>
  );
}
