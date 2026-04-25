'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, Loader2, Brain, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input }  from '@/components/ui/input';
import { Label }  from '@/components/ui/label';
import { cn }     from '@/lib/utils';
import { changePassword, extractApiError } from '@/lib/auth';

// ─── Schema ──────────────────────────────────────────────────────────────────

const schema = z
  .object({
    old_password:     z.string().min(1, 'Current password is required'),
    new_password:     z
      .string()
      .min(8, 'Must be at least 8 characters')
      .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
      .regex(/[a-z]/, 'Must contain at least one lowercase letter')
      .regex(/[0-9]/, 'Must contain at least one number')
      .regex(/[!@#$%^&*()_+\-=\[\]{}|;':",.<>?]/, 'Must contain at least one special character'),
    confirm_password: z.string().min(1, 'Please confirm your new password'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  });

type FormData = z.infer<typeof schema>;

// ─── Password strength indicator ─────────────────────────────────────────────

function getStrength(pw: string): { score: number; label: string; color: string } {
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[!@#$%^&*]/.test(pw)) score++;

  if (score <= 1) return { score, label: 'Weak',      color: 'bg-red-500' };
  if (score <= 2) return { score, label: 'Fair',      color: 'bg-orange-500' };
  if (score <= 3) return { score, label: 'Good',      color: 'bg-yellow-500' };
  if (score <= 4) return { score, label: 'Strong',    color: 'bg-emerald-500' };
  return               { score, label: 'Very strong', color: 'bg-green-600' };
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ChangePasswordPage() {
  const router = useRouter();
  const [showOld,  setShowOld]  = useState(false);
  const [showNew,  setShowNew]  = useState(false);
  const [showConf, setShowConf] = useState(false);
  const [serverError, setServerError] = useState('');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const newPw   = watch('new_password') ?? '';
  const strength = getStrength(newPw);

  async function onSubmit(data: FormData) {
    setServerError('');
    try {
      await changePassword(data.old_password, data.new_password);
      toast.success('Password changed successfully. Please log in again.');
      router.replace('/dashboard');
    } catch (error: unknown) {
      setServerError(extractApiError(error));
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center gap-2 mb-10">
          <div className="w-9 h-9 bg-hrms-600 rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-hrms-700">AI-HRMS</span>
        </div>

        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-card border border-slate-200 dark:border-slate-800 p-8 space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50">
              Change password
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Choose a strong password you haven't used before.
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {/* Current password */}
            <PasswordField
              id="old_password"
              label="Current password"
              show={showOld}
              onToggle={() => setShowOld((v) => !v)}
              error={errors.old_password?.message}
              disabled={isSubmitting}
              registration={register('old_password')}
            />

            {/* New password */}
            <div className="space-y-1.5">
              <PasswordField
                id="new_password"
                label="New password"
                show={showNew}
                onToggle={() => setShowNew((v) => !v)}
                error={errors.new_password?.message}
                disabled={isSubmitting}
                registration={register('new_password')}
              />
              {/* Strength bar */}
              {newPw.length > 0 && (
                <div className="space-y-1">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className={cn(
                          'h-1 flex-1 rounded-full transition-colors',
                          i <= strength.score ? strength.color : 'bg-slate-200',
                        )}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-slate-500">{strength.label}</p>
                </div>
              )}
            </div>

            {/* Confirm password */}
            <PasswordField
              id="confirm_password"
              label="Confirm new password"
              show={showConf}
              onToggle={() => setShowConf((v) => !v)}
              error={errors.confirm_password?.message}
              disabled={isSubmitting}
              registration={register('confirm_password')}
            />

            {/* Requirements checklist */}
            <ul className="space-y-1 text-xs text-slate-500">
              {[
                ['8+ characters',             newPw.length >= 8],
                ['Uppercase & lowercase',      /[A-Z]/.test(newPw) && /[a-z]/.test(newPw)],
                ['At least one number',        /[0-9]/.test(newPw)],
                ['At least one special char',  /[!@#$%^&*]/.test(newPw)],
              ].map(([label, met]) => (
                <li key={label as string} className="flex items-center gap-1.5">
                  <CheckCircle2
                    className={cn('h-3 w-3', met ? 'text-green-500' : 'text-slate-300')}
                  />
                  {label as string}
                </li>
              ))}
            </ul>

            {serverError && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {serverError}
              </div>
            )}

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-hrms-600 hover:bg-hrms-700 text-white h-11"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Updating…
                </>
              ) : (
                'Update password'
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}

// ─── Sub-component ────────────────────────────────────────────────────────────

interface PasswordFieldProps {
  id:           string;
  label:        string;
  show:         boolean;
  onToggle:     () => void;
  error?:       string;
  disabled?:    boolean;
  registration: ReturnType<ReturnType<typeof useForm>['register']>;
}

function PasswordField({
  id, label, show, onToggle, error, disabled, registration,
}: PasswordFieldProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={show ? 'text' : 'password'}
          disabled={disabled}
          className={cn('pr-10', error && 'border-red-400 focus-visible:ring-red-400')}
          {...registration}
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
