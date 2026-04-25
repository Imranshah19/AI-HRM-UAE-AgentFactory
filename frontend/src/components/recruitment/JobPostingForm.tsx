'use client';

import { useState, KeyboardEvent } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { X, Plus, Eye, EyeOff, ChevronDown, ChevronUp } from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Input }    from '@/components/ui/input';
import { Label }    from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge }    from '@/components/ui/badge';
import { Switch }   from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { JobPostingCreate, JobPostingResponse, EmploymentType } from '@/types/recruitment';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Department { id: string; name: string }
interface Designation { id: string; title: string }

interface Props {
  initialData?: Partial<JobPostingResponse>;
  departments:  Department[];
  designations: Designation[];
  onSubmit:     (data: JobPostingCreate) => void;
  isSubmitting?: boolean;
}

const EMPLOYMENT_TYPES: { value: EmploymentType; label: string }[] = [
  { value: 'full_time',   label: 'Full Time' },
  { value: 'part_time',   label: 'Part Time' },
  { value: 'contract',    label: 'Contract' },
  { value: 'internship',  label: 'Internship' },
  { value: 'remote',      label: 'Remote' },
];

// ─── Tag input ────────────────────────────────────────────────────────────────

function TagInput({
  value,
  onChange,
  placeholder,
}: {
  value:       string[];
  onChange:    (v: string[]) => void;
  placeholder: string;
}) {
  const [input, setInput] = useState('');

  function add() {
    const trimmed = input.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
    }
    setInput('');
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      add();
    } else if (e.key === 'Backspace' && !input && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  }

  return (
    <div className="flex flex-wrap gap-1.5 min-h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
      {value.map((tag) => (
        <Badge key={tag} variant="secondary" className="gap-1 pr-1">
          {tag}
          <button
            type="button"
            onClick={() => onChange(value.filter((t) => t !== tag))}
            className="rounded-full hover:bg-slate-300/50 p-0.5"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKey}
        onBlur={add}
        placeholder={value.length === 0 ? placeholder : 'Add more…'}
        className="flex-1 min-w-24 bg-transparent outline-none placeholder:text-muted-foreground"
      />
    </div>
  );
}

// ─── List input (requirements / responsibilities) ─────────────────────────────

function ListInput({
  value,
  onChange,
  placeholder,
}: {
  value:       string[];
  onChange:    (v: string[]) => void;
  placeholder: string;
}) {
  const [input, setInput] = useState('');

  function add() {
    const trimmed = input.trim();
    if (trimmed) { onChange([...value, trimmed]); }
    setInput('');
  }

  return (
    <div className="space-y-1.5">
      {value.map((item, i) => (
        <div key={i} className="flex items-center gap-2 group">
          <span className="text-slate-400 text-xs w-4">{i + 1}.</span>
          <span className="flex-1 text-sm text-slate-700">{item}</span>
          <button
            type="button"
            onClick={() => onChange(value.filter((_, j) => j !== i))}
            className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition-opacity"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())}
          placeholder={placeholder}
          className="h-8 text-sm"
        />
        <Button type="button" variant="outline" size="sm" onClick={add} className="h-8 shrink-0">
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

// ─── Preview panel ────────────────────────────────────────────────────────────

function PreviewPanel({ data }: { data: Partial<JobPostingCreate & { title: string }> }) {
  return (
    <div className="rounded-xl border bg-white p-6 space-y-5 text-sm">
      <div>
        <h2 className="text-xl font-bold text-slate-900">{data.title || 'Job Title'}</h2>
        <div className="flex flex-wrap gap-2 mt-2">
          {data.employment_type && (
            <Badge variant="secondary">
              {EMPLOYMENT_TYPES.find((t) => t.value === data.employment_type)?.label}
            </Badge>
          )}
          {data.location && <Badge variant="outline">{data.location}</Badge>}
          {data.is_salary_visible !== false && data.salary_range_min && (
            <Badge variant="outline" className="text-green-700 border-green-200 bg-green-50">
              PKR {data.salary_range_min.toLocaleString()}
              {data.salary_range_max ? ` – ${data.salary_range_max.toLocaleString()}` : '+'}
            </Badge>
          )}
        </div>
      </div>

      {data.description && (
        <div>
          <h3 className="font-semibold text-slate-700 mb-1.5">Description</h3>
          <p className="text-slate-600 whitespace-pre-wrap leading-relaxed">{data.description}</p>
        </div>
      )}

      {(data.requirements?.length ?? 0) > 0 && (
        <div>
          <h3 className="font-semibold text-slate-700 mb-1.5">Requirements</h3>
          <ul className="list-disc list-inside space-y-1 text-slate-600">
            {data.requirements!.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {(data.responsibilities?.length ?? 0) > 0 && (
        <div>
          <h3 className="font-semibold text-slate-700 mb-1.5">Responsibilities</h3>
          <ul className="list-disc list-inside space-y-1 text-slate-600">
            {data.responsibilities!.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {(data.skills_required?.length ?? 0) > 0 && (
        <div>
          <h3 className="font-semibold text-slate-700 mb-1.5">Required Skills</h3>
          <div className="flex flex-wrap gap-1.5">
            {data.skills_required!.map((s) => (
              <Badge key={s} variant="outline" className="text-blue-700 border-blue-200 bg-blue-50">
                {s}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {data.benefits && (
        <div>
          <h3 className="font-semibold text-slate-700 mb-1.5">Benefits</h3>
          <p className="text-slate-600 whitespace-pre-wrap leading-relaxed">{data.benefits}</p>
        </div>
      )}
    </div>
  );
}

// ─── Main Form ────────────────────────────────────────────────────────────────

export function JobPostingForm({
  initialData,
  departments,
  designations,
  onSubmit,
  isSubmitting = false,
}: Props) {
  const [showPreview,  setShowPreview]  = useState(false);
  const [showSalary,   setShowSalary]   = useState(
    !!(initialData?.salary_min || initialData?.salary_max),
  );
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { register, control, handleSubmit, watch, formState: { errors } } = useForm<JobPostingCreate>({
    defaultValues: {
      title:                initialData?.title                ?? '',
      department_id:        initialData?.department?.id       ?? null,
      designation_id:       initialData?.designation?.id      ?? null,
      location:             initialData?.location             ?? '',
      description:          initialData?.description          ?? '',
      requirements:         initialData?.requirements         ?? [],
      responsibilities:     initialData?.responsibilities     ?? [],
      benefits:             initialData?.benefits             ?? '',
      vacancies:            initialData?.vacancies            ?? 1,
      employment_type:      initialData?.employment_type      ?? 'full_time',
      experience_years_min: initialData?.experience_years_min ?? 0,
      experience_years_max: initialData?.experience_years_max ?? null,
      salary_range_min:     initialData?.salary_min           ?? null,
      salary_range_max:     initialData?.salary_max           ?? null,
      salary_visible:       initialData?.is_salary_visible    ?? false,
      skills_required:      initialData?.required_skills      ?? [],
      closing_date:         initialData?.closing_date         ?? null,
      is_internal:          initialData?.is_internal          ?? false,
    },
  });

  const formValues = watch();

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Preview toggle */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-800">Job Details</h3>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setShowPreview((v) => !v)}
          className="gap-1.5"
        >
          {showPreview ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          {showPreview ? 'Hide Preview' : 'Preview'}
        </Button>
      </div>

      {showPreview && (
        <PreviewPanel data={formValues} />
      )}

      {/* Core fields */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Title */}
        <div className="sm:col-span-2 space-y-1.5">
          <Label htmlFor="title">Job Title <span className="text-red-500">*</span></Label>
          <Input
            id="title"
            {...register('title', { required: 'Title is required' })}
            placeholder="e.g. Senior Software Engineer"
          />
          {errors.title && (
            <p className="text-xs text-red-500">{errors.title.message}</p>
          )}
        </div>

        {/* Department */}
        <div className="space-y-1.5">
          <Label>Department</Label>
          <Controller
            name="department_id"
            control={control}
            render={({ field }) => (
              <Select value={field.value ?? '__none__'} onValueChange={(v) => field.onChange(v === '__none__' ? null : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select department" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">None</SelectItem>
                  {departments.map((d) => (
                    <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>

        {/* Designation */}
        <div className="space-y-1.5">
          <Label>Designation</Label>
          <Controller
            name="designation_id"
            control={control}
            render={({ field }) => (
              <Select value={field.value ?? '__none__'} onValueChange={(v) => field.onChange(v === '__none__' ? null : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select designation" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">None</SelectItem>
                  {designations.map((d) => (
                    <SelectItem key={d.id} value={d.id}>{d.title}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>

        {/* Employment type */}
        <div className="space-y-1.5">
          <Label>Employment Type <span className="text-red-500">*</span></Label>
          <Controller
            name="employment_type"
            control={control}
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EMPLOYMENT_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>

        {/* Location */}
        <div className="space-y-1.5">
          <Label>Location</Label>
          <Input {...register('location')} placeholder="e.g. Karachi, Pakistan" />
        </div>

        {/* Vacancies */}
        <div className="space-y-1.5">
          <Label>Vacancies <span className="text-red-500">*</span></Label>
          <Input
            type="number"
            min={1}
            {...register('vacancies', { valueAsNumber: true, min: 1 })}
          />
        </div>

        {/* Closing date */}
        <div className="space-y-1.5">
          <Label>Closing Date</Label>
          <Input type="date" {...register('closing_date')} />
        </div>
      </div>

      {/* Experience range */}
      <div className="space-y-1.5">
        <Label>Experience Required (years)</Label>
        <div className="flex items-center gap-3">
          <Input
            type="number"
            min={0}
            placeholder="Min"
            className="w-24"
            {...register('experience_years_min', { valueAsNumber: true, min: 0 })}
          />
          <span className="text-slate-400 text-sm">to</span>
          <Input
            type="number"
            min={0}
            placeholder="Max (optional)"
            className="w-36"
            {...register('experience_years_max', { valueAsNumber: true })}
          />
          <span className="text-slate-500 text-sm">years</span>
        </div>
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <Label>Description <span className="text-red-500">*</span></Label>
        <Textarea
          rows={5}
          {...register('description', { required: 'Description is required' })}
          placeholder="Describe the role, team, and what success looks like…"
          className="resize-y"
        />
        {errors.description && (
          <p className="text-xs text-red-500">{errors.description.message}</p>
        )}
      </div>

      {/* Requirements */}
      <div className="space-y-1.5">
        <Label>Requirements</Label>
        <Controller
          name="requirements"
          control={control}
          render={({ field }) => (
            <ListInput
              value={field.value ?? []}
              onChange={field.onChange}
              placeholder="Add a requirement and press Enter…"
            />
          )}
        />
      </div>

      {/* Responsibilities */}
      <div className="space-y-1.5">
        <Label>Responsibilities</Label>
        <Controller
          name="responsibilities"
          control={control}
          render={({ field }) => (
            <ListInput
              value={field.value ?? []}
              onChange={field.onChange}
              placeholder="Add a responsibility and press Enter…"
            />
          )}
        />
      </div>

      {/* Skills */}
      <div className="space-y-1.5">
        <Label>Required Skills</Label>
        <Controller
          name="skills_required"
          control={control}
          render={({ field }) => (
            <TagInput
              value={field.value ?? []}
              onChange={field.onChange}
              placeholder="Type a skill and press Enter…"
            />
          )}
        />
        <p className="text-xs text-slate-500">These skills are used by the AI scorer to rank candidates.</p>
      </div>

      {/* Salary section */}
      <div className="rounded-lg border p-4 space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium">Salary Range</Label>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowSalary((v) => !v)}
            className="h-7 text-xs gap-1"
          >
            {showSalary ? 'Hide' : 'Set salary range'}
          </Button>
        </div>

        {showSalary && (
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs text-slate-500">Min (PKR)</Label>
              <Input
                type="number"
                min={0}
                {...register('salary_range_min', { valueAsNumber: true })}
                placeholder="e.g. 80000"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-slate-500">Max (PKR)</Label>
              <Input
                type="number"
                min={0}
                {...register('salary_range_max', { valueAsNumber: true })}
                placeholder="e.g. 150000"
              />
            </div>
            <div className="col-span-2 flex items-center gap-2">
              <Controller
                name="salary_visible"
                control={control}
                render={({ field }) => (
                  <Switch
                    checked={field.value ?? false}
                    onCheckedChange={field.onChange}
                    id="salary-visible"
                  />
                )}
              />
              <Label htmlFor="salary-visible" className="text-sm font-normal cursor-pointer">
                Show salary range to candidates
              </Label>
            </div>
          </div>
        )}
      </div>

      {/* Advanced / Benefits */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900 transition-colors"
        >
          {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          {showAdvanced ? 'Hide' : 'Show'} advanced options
        </button>

        {showAdvanced && (
          <div className="mt-4 space-y-4">
            {/* Benefits */}
            <div className="space-y-1.5">
              <Label>Benefits</Label>
              <Textarea
                rows={3}
                {...register('benefits')}
                placeholder="Health insurance, annual bonus, flexible hours…"
              />
            </div>

            {/* Internal posting */}
            <div className="flex items-center gap-2">
              <Controller
                name="is_internal"
                control={control}
                render={({ field }) => (
                  <Switch
                    checked={field.value ?? false}
                    onCheckedChange={field.onChange}
                    id="is-internal"
                  />
                )}
              />
              <div>
                <Label htmlFor="is-internal" className="cursor-pointer">Internal Posting Only</Label>
                <p className="text-xs text-slate-500">
                  Will not appear on the public careers portal.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Submit */}
      <div className="flex justify-end gap-3 pt-2 border-t">
        <Button type="submit" disabled={isSubmitting} className="min-w-28">
          {isSubmitting ? 'Saving…' : initialData?.id ? 'Update Posting' : 'Create Posting'}
        </Button>
      </div>
    </form>
  );
}
