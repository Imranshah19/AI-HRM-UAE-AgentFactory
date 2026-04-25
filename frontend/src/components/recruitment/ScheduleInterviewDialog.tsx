'use client';

import { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Calendar, Clock, Video, Users, MapPin } from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Input }    from '@/components/ui/input';
import { Label }    from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

import { useScheduleInterview } from '@/hooks/useRecruitment';
import type { InterviewMode, InterviewScheduleRequest } from '@/types/recruitment';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Interviewer {
  id:        string;
  full_name: string;
  photo_url?: string | null;
}

interface Props {
  open:          boolean;
  onOpenChange:  (open: boolean) => void;
  applicationId: string;
  candidateName: string;
  interviewers:  Interviewer[];
}

interface FormValues {
  scheduled_date:     string;
  scheduled_time:     string;
  duration_minutes:   number;
  mode:               InterviewMode;
  location_or_link?:  string;
  notes_for_candidate?: string;
  title?:             string;
}

const MODES: { value: InterviewMode; label: string; icon: React.ReactNode }[] = [
  { value: 'online',    label: 'Online',     icon: <Video   className="h-3.5 w-3.5" /> },
  { value: 'in_person', label: 'In Person',  icon: <Users   className="h-3.5 w-3.5" /> },
  { value: 'phone',     label: 'Phone Call', icon: <Clock   className="h-3.5 w-3.5" /> },
];

const DURATIONS = [30, 45, 60, 90, 120];

// ─── Component ────────────────────────────────────────────────────────────────

export function ScheduleInterviewDialog({
  open,
  onOpenChange,
  applicationId,
  candidateName,
  interviewers,
}: Props) {
  const [selectedInterviewerIds, setSelectedInterviewerIds] = useState<string[]>([]);
  const schedule = useScheduleInterview();

  const { register, control, handleSubmit, watch, reset, formState: { errors } } =
    useForm<FormValues>({
      defaultValues: {
        scheduled_date:   '',
        scheduled_time:   '10:00',
        duration_minutes: 60,
        mode:             'online',
      },
    });

  const mode = watch('mode');

  function toggleInterviewer(id: string) {
    setSelectedInterviewerIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
  }

  function onSubmit(values: FormValues) {
    if (selectedInterviewerIds.length === 0) return;

    const scheduledAt = `${values.scheduled_date}T${values.scheduled_time}:00`;

    const payload: InterviewScheduleRequest = {
      application_id:       applicationId,
      interviewer_ids:      selectedInterviewerIds,
      scheduled_at:         scheduledAt,
      duration_minutes:     values.duration_minutes,
      mode:                 values.mode,
      location_or_link:     values.location_or_link || undefined,
      notes_for_candidate:  values.notes_for_candidate || undefined,
      title:                values.title || undefined,
    };

    schedule.mutate(payload, {
      onSuccess: () => {
        reset();
        setSelectedInterviewerIds([]);
        onOpenChange(false);
      },
    });
  }

  const today = new Date().toISOString().split('T')[0];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Schedule Interview</DialogTitle>
          <DialogDescription>
            Set up an interview for <strong>{candidateName}</strong>. Invitations will be sent
            to all selected interviewers and the candidate.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
          {/* Title */}
          <div className="space-y-1.5">
            <Label>Interview Title (optional)</Label>
            <Input
              {...register('title')}
              placeholder="e.g. Technical Round 1, HR Screening"
            />
          </div>

          {/* Date & Time */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="date" className="flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-slate-400" />
                Date <span className="text-red-500">*</span>
              </Label>
              <Input
                id="date"
                type="date"
                min={today}
                {...register('scheduled_date', { required: 'Date is required' })}
              />
              {errors.scheduled_date && (
                <p className="text-xs text-red-500">{errors.scheduled_date.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="time" className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-slate-400" />
                Time <span className="text-red-500">*</span>
              </Label>
              <Input
                id="time"
                type="time"
                {...register('scheduled_time', { required: 'Time is required' })}
              />
            </div>
          </div>

          {/* Duration */}
          <div className="space-y-1.5">
            <Label>Duration</Label>
            <div className="flex gap-2 flex-wrap">
              <Controller
                name="duration_minutes"
                control={control}
                render={({ field }) => (
                  <>
                    {DURATIONS.map((d) => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => field.onChange(d)}
                        className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                          field.value === d
                            ? 'bg-slate-900 text-white border-slate-900'
                            : 'bg-white text-slate-700 border-slate-200 hover:border-slate-400'
                        }`}
                      >
                        {d < 60 ? `${d}m` : `${d / 60}h`}
                      </button>
                    ))}
                  </>
                )}
              />
            </div>
          </div>

          {/* Mode */}
          <div className="space-y-1.5">
            <Label>Interview Mode</Label>
            <Controller
              name="mode"
              control={control}
              render={({ field }) => (
                <div className="flex gap-2">
                  {MODES.map((m) => (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => field.onChange(m.value)}
                      className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border text-sm transition-colors ${
                        field.value === m.value
                          ? 'bg-slate-900 text-white border-slate-900'
                          : 'bg-white text-slate-700 border-slate-200 hover:border-slate-400'
                      }`}
                    >
                      {m.icon}
                      {m.label}
                    </button>
                  ))}
                </div>
              )}
            />
          </div>

          {/* Location / link */}
          <div className="space-y-1.5">
            <Label className="flex items-center gap-1.5">
              {mode === 'in_person'
                ? <><MapPin className="h-3.5 w-3.5 text-slate-400" /> Location</>
                : <><Video  className="h-3.5 w-3.5 text-slate-400" /> Meeting Link</>
              }
            </Label>
            <Input
              {...register('location_or_link')}
              placeholder={
                mode === 'in_person'
                  ? 'Conference Room A, Floor 3'
                  : 'https://meet.google.com/…'
              }
            />
          </div>

          {/* Interviewers */}
          <div className="space-y-1.5">
            <Label>
              Interviewers <span className="text-red-500">*</span>
            </Label>
            {interviewers.length === 0 ? (
              <p className="text-sm text-slate-500 italic">No interviewers available.</p>
            ) : (
              <div className="space-y-1 max-h-40 overflow-y-auto rounded-lg border p-2">
                {interviewers.map((iv) => {
                  const selected = selectedInterviewerIds.includes(iv.id);
                  return (
                    <button
                      key={iv.id}
                      type="button"
                      onClick={() => toggleInterviewer(iv.id)}
                      className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm transition-colors ${
                        selected
                          ? 'bg-slate-900 text-white'
                          : 'hover:bg-slate-50 text-slate-700'
                      }`}
                    >
                      <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 ${
                        selected ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'
                      }`}>
                        {iv.full_name.charAt(0)}
                      </div>
                      <span className="flex-1 text-left truncate">{iv.full_name}</span>
                      {selected && <Badge variant="secondary" className="text-xs py-0">Selected</Badge>}
                    </button>
                  );
                })}
              </div>
            )}
            {selectedInterviewerIds.length === 0 && (
              <p className="text-xs text-red-500">Select at least one interviewer.</p>
            )}
          </div>

          {/* Notes for candidate */}
          <div className="space-y-1.5">
            <Label>Notes for Candidate (included in invitation email)</Label>
            <Textarea
              rows={2}
              {...register('notes_for_candidate')}
              placeholder="Please bring your portfolio, ID proof…"
              className="resize-none text-sm"
            />
          </div>

          {/* Preview summary */}
          {watch('scheduled_date') && watch('scheduled_time') && (
            <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-800 space-y-0.5">
              <p className="font-semibold">Invitation will be sent to:</p>
              <p>• Candidate: {candidateName}</p>
              {selectedInterviewerIds.map((id) => {
                const iv = interviewers.find((i) => i.id === id);
                return iv ? <p key={id}>• {iv.full_name}</p> : null;
              })}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2 border-t">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={schedule.isPending || selectedInterviewerIds.length === 0}
            >
              {schedule.isPending ? 'Scheduling…' : 'Schedule & Send Invitations'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
