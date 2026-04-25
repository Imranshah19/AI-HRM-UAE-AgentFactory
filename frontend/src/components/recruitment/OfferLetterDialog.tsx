'use client';

import { useForm } from 'react-hook-form';
import { FileText, Send } from 'lucide-react';

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

import { useGenerateOffer } from '@/hooks/useRecruitment';
import type { OfferLetterRequest } from '@/types/recruitment';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Props {
  open:          boolean;
  onOpenChange:  (open: boolean) => void;
  applicationId: string;
  candidateName: string;
  jobTitle:      string;
}

interface FormValues {
  offered_salary:    number;
  joining_date:      string;
  offer_expiry_date: string;
  additional_terms?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function OfferLetterDialog({
  open,
  onOpenChange,
  applicationId,
  candidateName,
  jobTitle,
}: Props) {
  const generateOffer = useGenerateOffer();

  const { register, handleSubmit, reset, watch, formState: { errors } } =
    useForm<FormValues>({
      defaultValues: {
        offered_salary:    0,
        joining_date:      '',
        offer_expiry_date: '',
        additional_terms:  '',
      },
    });

  const values = watch();
  const today  = new Date().toISOString().split('T')[0];

  function onSubmit(data: FormValues) {
    const payload: OfferLetterRequest = {
      application_id:    applicationId,
      offered_salary:    data.offered_salary,
      joining_date:      data.joining_date,
      offer_expiry_date: data.offer_expiry_date,
      additional_terms:  data.additional_terms || undefined,
    };

    generateOffer.mutate(payload, {
      onSuccess: () => {
        reset();
        onOpenChange(false);
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-slate-600" />
            Generate Offer Letter
          </DialogTitle>
          <DialogDescription>
            A formal offer letter will be generated as a PDF and emailed to{' '}
            <strong>{candidateName}</strong> for the <strong>{jobTitle}</strong> position.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
          {/* Offered salary */}
          <div className="space-y-1.5">
            <Label htmlFor="salary">
              Offered Salary (PKR / month) <span className="text-red-500">*</span>
            </Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
                PKR
              </span>
              <Input
                id="salary"
                type="number"
                min={1}
                className="pl-12"
                {...register('offered_salary', {
                  valueAsNumber: true,
                  required:      'Salary is required',
                  min:           { value: 1, message: 'Must be greater than 0' },
                })}
                placeholder="e.g. 120000"
              />
            </div>
            {errors.offered_salary && (
              <p className="text-xs text-red-500">{errors.offered_salary.message}</p>
            )}
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="joining">
                Joining Date <span className="text-red-500">*</span>
              </Label>
              <Input
                id="joining"
                type="date"
                min={today}
                {...register('joining_date', { required: 'Joining date is required' })}
              />
              {errors.joining_date && (
                <p className="text-xs text-red-500">{errors.joining_date.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="expiry">
                Offer Expiry <span className="text-red-500">*</span>
              </Label>
              <Input
                id="expiry"
                type="date"
                min={today}
                {...register('offer_expiry_date', { required: 'Expiry date is required' })}
              />
              {errors.offer_expiry_date && (
                <p className="text-xs text-red-500">{errors.offer_expiry_date.message}</p>
              )}
            </div>
          </div>

          {/* Additional terms */}
          <div className="space-y-1.5">
            <Label>Additional Terms (optional)</Label>
            <Textarea
              rows={3}
              {...register('additional_terms')}
              placeholder="Probation period of 3 months, annual performance review, remote work policy…"
              className="resize-none text-sm"
            />
          </div>

          {/* Preview summary */}
          {values.offered_salary > 0 && values.joining_date && (
            <div className="rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-800 space-y-1">
              <p className="font-semibold">Offer Summary</p>
              <p>Candidate: {candidateName}</p>
              <p>Position: {jobTitle}</p>
              <p>Salary: PKR {values.offered_salary.toLocaleString()} / month</p>
              <p>
                Joining:{' '}
                {new Date(values.joining_date).toLocaleDateString('en-PK', {
                  day: '2-digit', month: 'long', year: 'numeric',
                })}
              </p>
              {values.offer_expiry_date && (
                <p>
                  Valid until:{' '}
                  {new Date(values.offer_expiry_date).toLocaleDateString('en-PK', {
                    day: '2-digit', month: 'long', year: 'numeric',
                  })}
                </p>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={generateOffer.isPending}
              className="gap-2"
            >
              <Send className="h-4 w-4" />
              {generateOffer.isPending ? 'Generating…' : 'Generate & Send'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
